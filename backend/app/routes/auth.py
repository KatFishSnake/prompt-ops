import secrets

import redis as redis_lib
import resend
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_jwt, get_current_user
from ..config import settings
from ..database import get_db
from ..models import Prompt, PromptVersion, User

router = APIRouter(prefix="/auth")

redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)

DEMO_PROMPTS = [
    {
        "name": "customer-support-demo",
        "description": "Handles customer support inquiries. Trained to be empathetic and solution-oriented.",
        "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan.\n\nRules:\n- Always be empathetic and solution-oriented\n- Acknowledge the user's frustration before offering solutions\n- Provide step-by-step instructions when applicable\n- If you can't resolve the issue, escalate to a human agent",
        "model_config": {"model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 512},
    },
    {
        "name": "code-review-demo",
        "description": "Reviews code and provides feedback on quality, security, and best practices.",
        "content": "You are a code review assistant. Review the following code and provide feedback on quality, security, and best practices.\n\nLanguage: {{language}}\nContext: {{context}}",
        "model_config": {"model": "gpt-4o-mini", "temperature": 0.2, "max_tokens": 1024},
    },
    {
        "name": "content-summarizer-demo",
        "description": "Summarizes long-form content into concise briefs.",
        "content": "Summarize the following content in 2-3 bullet points. Focus on actionable insights for a {{team_type}} team.\n\nTone: {{tone}}",
        "model_config": {"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 256},
    },
]


def _set_auth_cookie(response, token: str):
    is_secure = settings.frontend_url.startswith("https")
    response.set_cookie(
        key="promptops_token",
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
        max_age=604800,  # 7 days
    )
    return response


async def _seed_demo_prompts(user_id, db: AsyncSession):
    for p_data in DEMO_PROMPTS:
        # Skip if prompt with this name already exists for user (even if soft-deleted)
        existing = await db.execute(
            select(Prompt).where(Prompt.name == p_data["name"], Prompt.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            continue

        prompt = Prompt(
            name=p_data["name"],
            description=p_data["description"],
            user_id=user_id,
        )
        db.add(prompt)
        await db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            content=p_data["content"],
            model_config_json=p_data["model_config"],
            is_active=True,
            created_by="seed",
        )
        db.add(version)


async def _get_or_create_user(email: str, db: AsyncSession) -> tuple[User, bool]:
    """Returns (user, is_new)."""
    # Try to create
    api_key = secrets.token_urlsafe(32)
    user = User(email=email, api_key=api_key)
    db.add(user)
    try:
        await db.flush()
        return user, True
    except IntegrityError:
        await db.rollback()
        # User already exists (concurrent verify or repeat login)
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one(), False


class MagicLinkRequest(BaseModel):
    email: str


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkRequest):
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")

    # Rate limit: max 3 per email per 10 minutes
    rate_key = f"magic_rate:{email}"
    current = redis_client.get(rate_key)
    if current and int(current) >= 3:
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a few minutes.")
    pipe = redis_client.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, 600)  # 10 minutes
    pipe.execute()

    # Generate token
    token = secrets.token_urlsafe(48)
    redis_client.setex(f"magic:{token}", 900, email)  # 15 min TTL

    # Send email via Resend
    verify_url = f"{settings.frontend_url}/api/auth/verify?token={token}"

    if settings.resend_api_key:
        resend.api_key = settings.resend_api_key
        try:
            r = resend.Emails.send({
                "from": "PromptOps <onboarding@resend.dev>",
                "to": [email],
                "subject": "Your PromptOps login link",
                "html": f'<p>Click to log in to PromptOps:</p><p><a href="{verify_url}">Log in to PromptOps</a></p><p>This link expires in 15 minutes.</p>',
            })
            print(f"📧 Resend response: {r}")  # noqa: T201
        except Exception as e:
            print(f"❌ Resend error: {e}")  # noqa: T201
            raise HTTPException(status_code=500, detail=f"Failed to send email: {e}") from e
    else:
        print(f"\n🔗 Magic link for {email}: {verify_url}\n")  # noqa: T201

    return {"status": "sent"}


@router.get("/verify")
async def verify_magic_link(token: str, db: AsyncSession = Depends(get_db)):
    # Atomic get + delete
    pipe = redis_client.pipeline()
    pipe.get(f"magic:{token}")
    pipe.delete(f"magic:{token}")
    results = pipe.execute()
    email = results[0]

    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user, is_new = await _get_or_create_user(email, db)

    if is_new:
        await _seed_demo_prompts(user.id, db)

    await db.commit()

    jwt_token = create_jwt(str(user.id))
    response = RedirectResponse(url="/", status_code=302)
    _set_auth_cookie(response, jwt_token)
    return response


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "api_key": current_user.api_key}


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("promptops_token", path="/")
    return response


@router.get("/dev-login")
async def dev_login(db: AsyncSession = Depends(get_db)):
    if not settings.dev_auth_email:
        raise HTTPException(status_code=404, detail="Dev login not enabled")

    email = settings.dev_auth_email
    user, is_new = await _get_or_create_user(email, db)
    if is_new:
        await _seed_demo_prompts(user.id, db)
    await db.commit()

    jwt_token = create_jwt(str(user.id))
    response = RedirectResponse(url="/", status_code=302)
    _set_auth_cookie(response, jwt_token)
    return response
