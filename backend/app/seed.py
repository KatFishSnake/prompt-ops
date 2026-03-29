"""Seed script: populates sample prompts with versions."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Prompt, PromptVersion

engine = create_engine(settings.database_url_sync)
SessionLocal = sessionmaker(engine)

SEED_PROMPTS = [
    {
        "name": "customer-support-agent",
        "description": "Handles customer support inquiries for a SaaS product. Trained to be empathetic and solution-oriented.",
        "versions": [
            {
                "version_number": 1,
                "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan. Be professional and concise.",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 512},
                "is_active": False,
            },
            {
                "version_number": 2,
                "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan.\n\nRules:\n- Always be empathetic and solution-oriented\n- Acknowledge the user's frustration before offering solutions\n- Provide step-by-step instructions when applicable\n- If you can't resolve the issue, escalate to a human agent",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 512},
                "is_active": True,
            },
            {
                "version_number": 3,
                "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan.\n\nRules:\n- Always be empathetic and solution-oriented\n- Acknowledge the user's frustration before offering solutions\n- Provide step-by-step instructions when applicable\n- If you can't resolve the issue, escalate to a human agent\n- Always end with a follow-up question to ensure the user's issue is fully resolved\n- Use the user's name if available in the conversation",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 768},
                "is_active": False,
            },
        ],
    },
    {
        "name": "code-review-assistant",
        "description": "Reviews pull requests and provides constructive feedback on code quality, security, and best practices.",
        "versions": [
            {
                "version_number": 1,
                "content": "You are a code review assistant. Review the following code and provide feedback on quality, security, and best practices.\n\nLanguage: {{language}}\nContext: {{context}}",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.2, "max_tokens": 1024},
                "is_active": True,
            },
        ],
    },
    {
        "name": "content-summarizer",
        "description": "Summarizes long-form content into concise, actionable briefs for product teams.",
        "versions": [
            {
                "version_number": 1,
                "content": "Summarize the following content in 2-3 bullet points. Focus on actionable insights for a {{team_type}} team.\n\nTone: {{tone}}",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 256},
                "is_active": True,
            },
        ],
    },
]


def seed():
    with SessionLocal() as db:
        existing = db.execute(select(Prompt).limit(1)).scalar_one_or_none()
        if existing:
            print("Database already seeded, skipping.")
            return

        print("Seeding database...")

        for prompt_data in SEED_PROMPTS:
            prompt = Prompt(
                name=prompt_data["name"],
                description=prompt_data["description"],
            )
            db.add(prompt)
            db.flush()

            for v_data in prompt_data["versions"]:
                version = PromptVersion(
                    prompt_id=prompt.id,
                    version_number=v_data["version_number"],
                    content=v_data["content"],
                    model_config_json=v_data["model_config"],
                    is_active=v_data["is_active"],
                    created_by="seed",
                )
                db.add(version)

        db.commit()
        print(f"Seeded: {len(SEED_PROMPTS)} prompts with versions")


if __name__ == "__main__":
    seed()
