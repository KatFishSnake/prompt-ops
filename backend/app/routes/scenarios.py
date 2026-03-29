import json
import uuid

import jinja2
import openai
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..models import Prompt, PromptVersion, ScenarioJob, ScenarioJobItem
from ..schemas import (
    GenerateScenariosRequest,
    GenerateScenariosResponse,
    RunScenariosRequest,
    RunScenariosResponse,
    ScenarioItem,
    ScenarioJobItemOut,
    ScenarioJobOut,
)

router = APIRouter()

SCENARIO_GEN_PROMPT = """You are a test scenario generator. Given a description of an AI assistant's domain, generate {count} diverse test scenarios.

Each scenario should have:
- "role": A short persona label (e.g., "Angry customer", "Confused new user", "Technical expert")
- "message": A realistic user message that this persona would send
- "variables": An object with values for these template variables: {variables}

Requirements:
- Cover diverse personas: happy, angry, confused, technical, non-technical, edge cases
- Include at least one adversarial or off-topic message
- Messages should feel like real user input, not test data
- Each message should be 1-3 sentences
- Variable values should be realistic and varied across scenarios

Domain description: {description}

Return ONLY a JSON array of scenario objects. No markdown, no explanation."""


def extract_template_variables(content: str) -> list[str]:
    """Extract Jinja2 template variable names from prompt content."""
    try:
        env = jinja2.Environment(autoescape=True)
        ast = env.parse(content)
        return sorted(jinja2.meta.find_undeclared_variables(ast))
    except Exception:
        return []


@router.post("/prompts/{prompt_id}/generate-scenarios", response_model=GenerateScenariosResponse)
async def generate_scenarios(
    prompt_id: uuid.UUID, body: GenerateScenariosRequest, db: AsyncSession = Depends(get_db)
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key configured. Add OPENAI_API_KEY to .env and restart.",
        )

    # Get prompt
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Use specified version or fall back to active
    if body.version_id:
        version_result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.id == body.version_id, PromptVersion.prompt_id == prompt_id
            )
        )
    else:
        version_result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.prompt_id == prompt_id, PromptVersion.is_active == True
            )
        )
    target_version = version_result.scalar_one_or_none()
    if not target_version:
        raise HTTPException(status_code=400, detail="Version not found.")

    # Extract template variables
    variables = extract_template_variables(target_version.content)
    variables_str = ", ".join(variables) if variables else "none (no template variables used)"

    # Generate scenarios via LLM
    gen_prompt = SCENARIO_GEN_PROMPT.format(
        count=body.count,
        variables=variables_str,
        description=body.description,
    )

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": gen_prompt}],
            temperature=0.8,
            max_tokens=4096,
            timeout=30,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        scenarios_data = json.loads(raw)
        if not isinstance(scenarios_data, list):
            raise ValueError("Expected a JSON array")

        scenarios = [
            ScenarioItem(
                role=s.get("role", "User"),
                message=s.get("message", ""),
                variables=s.get("variables", {}),
            )
            for s in scenarios_data
            if s.get("message")
        ]

        return GenerateScenariosResponse(scenarios=scenarios)

    except openai.AuthenticationError as e:
        raise HTTPException(
            status_code=400, detail="Invalid API key. Check your OPENAI_API_KEY."
        ) from e
    except openai.RateLimitError as e:
        raise HTTPException(
            status_code=429, detail="Rate limited by OpenAI. Try again in a moment."
        ) from e
    except openai.APITimeoutError as e:
        raise HTTPException(status_code=408, detail="Generation timed out. Try again.") from e
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=502, detail="Failed to parse generated scenarios. Try again."
        ) from e


@router.post("/prompts/{prompt_id}/run-scenarios", response_model=RunScenariosResponse)
async def run_scenarios(
    prompt_id: uuid.UUID, body: RunScenariosRequest, db: AsyncSession = Depends(get_db)
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key configured. Add OPENAI_API_KEY to .env and restart.",
        )

    # Get prompt
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Use specified version or fall back to active
    if body.version_id:
        version_result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.id == body.version_id, PromptVersion.prompt_id == prompt_id
            )
        )
    else:
        version_result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.prompt_id == prompt_id, PromptVersion.is_active == True
            )
        )
    target_version = version_result.scalar_one_or_none()
    if not target_version:
        raise HTTPException(status_code=400, detail="Version not found.")

    # Create scenario job
    job = ScenarioJob(
        prompt_id=prompt_id,
        prompt_version_id=target_version.id,
        status="pending",
        total=len(body.scenarios),
    )
    db.add(job)
    await db.flush()

    # Create job items
    for scenario in body.scenarios:
        item = ScenarioJobItem(
            scenario_job_id=job.id,
            status="pending",
            role=scenario.role,
            message=scenario.message,
            variables_json=scenario.variables,
        )
        db.add(item)

    await db.commit()

    # Dispatch Celery task
    from ..tasks import run_scenarios_task
    run_scenarios_task.delay(str(job.id))

    return RunScenariosResponse(job_id=job.id)


@router.get("/scenario-jobs/{job_id}", response_model=ScenarioJobOut)
async def get_scenario_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScenarioJob)
        .where(ScenarioJob.id == job_id)
        .options(selectinload(ScenarioJob.items))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Scenario job not found")

    completed = sum(1 for item in job.items if item.status in ("success", "failed"))

    items_out = [
        ScenarioJobItemOut(
            id=item.id,
            status=item.status,
            role=item.role,
            message=item.message,
            trace_id=item.trace_id,
            output_preview=item.output_preview,
            latency_ms=item.latency_ms,
            error=item.error,
        )
        for item in job.items
    ]

    return ScenarioJobOut(
        id=job.id,
        prompt_id=job.prompt_id,
        prompt_version_id=job.prompt_version_id,
        status=job.status,
        total=job.total,
        completed=completed,
        created_at=job.created_at,
        completed_at=job.completed_at,
        items=items_out,
    )
