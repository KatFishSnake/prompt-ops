import time
import uuid
from datetime import UTC, datetime

import openai
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Template
from sqlalchemy import func as sql_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_api_key_user, get_current_user
from ..config import settings
from ..database import get_db
from ..models import Prompt, PromptVersion, ReplayJob, ReplayResult, ScenarioJob, User
from ..schemas import (
    PlaygroundRequest,
    PlaygroundResponse,
    PromoteRequest,
    PromptCreate,
    PromptListItem,
    PromptOut,
    PromptVersionCreate,
    PromptVersionOut,
    ServeOut,
)

router = APIRouter()


@router.post("/prompts", response_model=PromptOut)
async def create_prompt(body: PromptCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = await db.execute(
        select(Prompt).where(Prompt.name == body.name, Prompt.deleted_at.is_(None), Prompt.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Prompt name already exists")

    prompt = Prompt(name=body.name, description=body.description, user_id=current_user.id)
    db.add(prompt)
    await db.flush()

    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content="",
        is_active=True,
        created_by="user",
    )
    db.add(version)
    await db.commit()

    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt.id).options(selectinload(Prompt.versions))
    )
    return result.scalar_one()


@router.get("/prompts", response_model=list[PromptListItem])
async def list_prompts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Prompt)
        .where(Prompt.deleted_at.is_(None))
        .where(Prompt.user_id == current_user.id)
        .options(selectinload(Prompt.versions))
        .order_by(Prompt.updated_at.desc())
    )
    prompts = result.scalars().all()

    items = []
    for p in prompts:
        active_v = next((v for v in p.versions if v.is_active), None)
        version_count = len(p.versions)

        # Get latest replay for this prompt
        latest_replay = None
        replay_result = await db.execute(
            select(ReplayJob)
            .where(ReplayJob.prompt_id == p.id, ReplayJob.status == "complete")
            .order_by(ReplayJob.completed_at.desc())
            .limit(1)
        )
        replay_job = replay_result.scalar_one_or_none()
        if replay_job:
            results = await db.execute(
                select(ReplayResult).where(
                    ReplayResult.replay_job_id == replay_job.id,
                    ReplayResult.status == "success",
                )
            )
            replay_results = results.scalars().all()
            improved = sum(1 for r in replay_results if r.score_delta and r.score_delta > 0)
            regressed = sum(1 for r in replay_results if r.score_delta and r.score_delta < 0)
            unchanged = sum(
                1 for r in replay_results if r.score_delta is not None and r.score_delta == 0
            )
            latest_replay = {
                "job_id": str(replay_job.id),
                "source_version_id": str(replay_job.source_version_id),
                "target_version_id": str(replay_job.target_version_id),
                "improved": improved,
                "regressed": regressed,
                "unchanged": unchanged,
            }

        items.append(
            PromptListItem(
                id=p.id,
                name=p.name,
                description=p.description,
                created_at=p.created_at,
                updated_at=p.updated_at,
                version_count=version_count,
                active_version=active_v.version_number if active_v else None,
                latest_replay=latest_replay,
            )
        )
    return items


@router.get("/prompts/serve/{name}", response_model=ServeOut)
async def serve_active(name: str, db: AsyncSession = Depends(get_db), api_key_user: User = Depends(get_api_key_user)):
    result = await db.execute(
        select(Prompt).where(Prompt.name == name, Prompt.deleted_at.is_(None), Prompt.user_id == api_key_user.id)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version_result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.prompt_id == prompt.id, PromptVersion.is_active == True
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="No active version")

    return ServeOut(
        prompt_name=prompt.name,
        version_number=version.version_number,
        content=version.content,
        model_config_json=version.model_config_json,
    )


@router.get("/prompts/{prompt_id}", response_model=PromptOut)
async def get_prompt(prompt_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == current_user.id).options(selectinload(Prompt.versions))
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("/prompts/{prompt_id}/versions", response_model=PromptVersionOut)
async def create_version(
    prompt_id: uuid.UUID, body: PromptVersionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == current_user.id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    max_version = await db.execute(
        select(sql_func.max(PromptVersion.version_number)).where(
            PromptVersion.prompt_id == prompt_id
        )
    )
    current_max = max_version.scalar() or 0

    version = PromptVersion(
        prompt_id=prompt_id,
        version_number=current_max + 1,
        content=body.content,
        model_config_json=body.model_config_json,
        is_active=False,
        created_by="user",
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


@router.put("/prompts/{prompt_id}/versions/{version_id}", response_model=PromptVersionOut)
async def update_version(
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
    body: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify prompt ownership
    prompt_result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == current_user.id)
    )
    if not prompt_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Prompt not found")

    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.id == version_id, PromptVersion.prompt_id == prompt_id
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    version.content = body.content
    version.model_config_json = body.model_config_json
    await db.commit()
    await db.refresh(version)
    return version


@router.post("/prompts/{prompt_id}/promote", response_model=PromptVersionOut)
async def promote_version(
    prompt_id: uuid.UUID, body: PromoteRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Verify prompt ownership
    prompt_result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == current_user.id)
    )
    if not prompt_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Prompt not found")

    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.prompt_id == prompt_id, PromptVersion.is_active == True
        )
    )
    current_active = result.scalar_one_or_none()
    if current_active:
        current_active.is_active = False

    target_result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.id == body.version_id, PromptVersion.prompt_id == prompt_id
        )
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")

    target.is_active = True
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.deleted_at.is_(None), Prompt.user_id == current_user.id)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Block if running jobs exist
    running_replays = await db.execute(
        select(ReplayJob).where(
            ReplayJob.prompt_id == prompt_id,
            ReplayJob.status.in_(["pending", "running"]),
        )
    )
    running_scenarios = await db.execute(
        select(ScenarioJob).where(
            ScenarioJob.prompt_id == prompt_id,
            ScenarioJob.status.in_(["pending", "running"]),
        )
    )
    if running_replays.scalar_one_or_none() or running_scenarios.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Stop running replay/scenario jobs before deleting"
        )

    prompt.deleted_at = datetime.now(UTC)
    await db.commit()
    return {"status": "deleted"}


@router.post("/prompts/{prompt_id}/playground", response_model=PlaygroundResponse)
async def playground(prompt_id: uuid.UUID, body: PlaygroundRequest, current_user: User = Depends(get_current_user)):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key configured. Add OPENAI_API_KEY to .env and restart.",
        )

    # Render template with variables
    try:
        rendered = Template(body.content).render(**body.variables)
    except Exception:
        rendered = body.content

    model_config = body.model_config_data or {}
    model = model_config.get("model", "gpt-4o-mini")
    temperature = model_config.get("temperature", 0.7)
    max_tokens = model_config.get("max_tokens", 1024)

    messages = [
        {"role": "system", "content": rendered},
        {"role": "user", "content": body.user_message},
    ]

    start = time.time()
    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30,
        )
        output = response.choices[0].message.content
        latency_ms = int((time.time() - start) * 1000)
        return PlaygroundResponse(output=output, latency_ms=latency_ms)
    except openai.AuthenticationError as e:
        raise HTTPException(
            status_code=400, detail="Invalid API key. Check your OPENAI_API_KEY."
        ) from e
    except openai.RateLimitError as e:
        raise HTTPException(
            status_code=400, detail="Rate limited by OpenAI. Try again in a moment."
        ) from e
    except openai.APITimeoutError as e:
        raise HTTPException(status_code=408, detail="Request timed out after 30 seconds.") from e
