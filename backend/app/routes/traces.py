from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_api_key_user, get_current_user
from ..database import get_db
from ..models import Prompt, PromptVersion, Trace, User
from ..schemas import TraceBatchInput, TraceOut

router = APIRouter()


@router.post("/traces", response_model=list[TraceOut])
async def ingest_traces(
    body: TraceBatchInput,
    db: AsyncSession = Depends(get_db),
    api_key_user: User = Depends(get_api_key_user),
):
    traces = []
    for t in body.traces:
        prompt_id = None
        prompt_version_id = None

        if t.prompt_name:
            result = await db.execute(
                select(Prompt).where(
                    Prompt.name == t.prompt_name, Prompt.user_id == api_key_user.id
                )
            )
            prompt = result.scalar_one_or_none()
            if prompt:
                prompt_id = prompt.id
                version_result = await db.execute(
                    select(PromptVersion).where(
                        PromptVersion.prompt_id == prompt.id,
                        PromptVersion.is_active == True,
                    )
                )
                active_version = version_result.scalar_one_or_none()
                if active_version:
                    prompt_version_id = active_version.id

        trace = Trace(
            user_id=api_key_user.id,
            prompt_id=prompt_id,
            prompt_version_id=prompt_version_id,
            input=t.input,
            output=t.output,
            model=t.model,
            latency_ms=t.latency_ms,
            metadata_json=t.metadata,
        )
        db.add(trace)
        traces.append(trace)

    await db.commit()
    for trace in traces:
        await db.refresh(trace)
    return traces


@router.get("/traces", response_model=list[TraceOut])
async def list_traces(
    prompt_name: str | None = Query(None),
    prompt_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Trace)
        .where(Trace.user_id == current_user.id)
        .options(selectinload(Trace.prompt))
        .order_by(Trace.created_at.desc())
    )

    if prompt_name:
        result = await db.execute(
            select(Prompt).where(Prompt.name == prompt_name, Prompt.user_id == current_user.id)
        )
        prompt = result.scalar_one_or_none()
        if prompt:
            query = query.where(Trace.prompt_id == prompt.id)
        else:
            return []

    if prompt_id:
        query = query.where(Trace.prompt_id == prompt_id)

    result = await db.execute(query)
    traces = result.scalars().all()
    return [
        TraceOut(
            id=t.id,
            prompt_id=t.prompt_id,
            prompt_version_id=t.prompt_version_id,
            prompt_name=t.prompt.name if t.prompt else None,
            input=t.input,
            output=t.output,
            model=t.model,
            latency_ms=t.latency_ms,
            metadata_json=t.metadata_json,
            created_at=t.created_at,
        )
        for t in traces
    ]
