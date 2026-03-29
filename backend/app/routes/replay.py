import asyncio
import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..auth import get_current_user
from ..config import settings
from ..database import async_session, get_db
from ..models import Prompt, PromptVersion, ReplayJob, ReplayResult, Trace, User
from ..schemas import (
    JudgeDiscussRequest,
    JudgeDiscussResponse,
    ReplayJobOut,
    ReplayRequest,
    ReplayResultOut,
    RerunTraceRequest,
    RerunTraceResponse,
)
from ..tasks import call_llm, run_judge, run_replay_task

router = APIRouter()


def build_replay_job_out(
    job: ReplayJob,
    results: list[ReplayResult],
    traces_map: dict,
    prompt_name: str = "",
    source_version_number: int | None = None,
    target_version_number: int | None = None,
) -> ReplayJobOut:
    success_results = [r for r in results if r.status == "success"]
    improved = sum(1 for r in success_results if r.score_delta and r.score_delta > 0)
    regressed = sum(1 for r in success_results if r.score_delta and r.score_delta < 0)
    unchanged = sum(1 for r in success_results if r.score_delta is not None and r.score_delta == 0)
    failed = sum(1 for r in results if r.status == "failed")

    avg_original = None
    avg_replayed = None
    scored = [
        r for r in success_results if r.original_score is not None and r.replayed_score is not None
    ]
    if scored:
        avg_original = sum(r.original_score for r in scored) / len(scored)
        avg_replayed = sum(r.replayed_score for r in scored) / len(scored)

    result_outs = []
    for r in results:
        trace_input = traces_map.get(r.trace_id)
        result_outs.append(
            ReplayResultOut(
                id=r.id,
                replay_job_id=r.replay_job_id,
                trace_id=r.trace_id,
                status=r.status,
                original_output=r.original_output,
                replayed_output=r.replayed_output,
                original_score=r.original_score,
                replayed_score=r.replayed_score,
                score_delta=r.score_delta,
                judge_reasoning=r.judge_reasoning,
                error=r.error,
                completed_at=r.completed_at,
                trace_input=trace_input,
            )
        )

    return ReplayJobOut(
        id=job.id,
        prompt_id=job.prompt_id,
        source_version_id=job.source_version_id,
        target_version_id=job.target_version_id,
        status=job.status,
        trace_count=job.trace_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        results=result_outs,
        improved=improved,
        unchanged=unchanged,
        regressed=regressed,
        failed=failed,
        avg_original_score=avg_original,
        avg_replayed_score=avg_replayed,
        prompt_name=prompt_name,
        source_version_number=source_version_number,
        target_version_number=target_version_number,
    )


@router.post("/replay", response_model=ReplayJobOut)
async def start_replay(body: ReplayRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validate prompt and versions exist
    prompt = await db.execute(select(Prompt).where(Prompt.id == body.prompt_id, Prompt.user_id == current_user.id))
    if not prompt.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Prompt not found")

    for vid in [body.source_version_id, body.target_version_id]:
        v = await db.execute(
            select(PromptVersion).where(
                PromptVersion.id == vid, PromptVersion.prompt_id == body.prompt_id
            )
        )
        if not v.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Version {vid} not found for this prompt")

    # Get traces for this prompt
    traces_result = await db.execute(select(Trace).where(Trace.prompt_id == body.prompt_id))
    traces = traces_result.scalars().all()
    if not traces:
        raise HTTPException(status_code=400, detail="No traces found for this prompt")

    # Create replay job
    job = ReplayJob(
        prompt_id=body.prompt_id,
        source_version_id=body.source_version_id,
        target_version_id=body.target_version_id,
        status="pending",
        trace_count=len(traces),
        user_id=current_user.id,
    )
    db.add(job)
    await db.flush()

    # Create pending results for each trace
    for trace in traces:
        result = ReplayResult(
            replay_job_id=job.id,
            trace_id=trace.id,
            status="pending",
            original_output=trace.output,
        )
        db.add(result)

    await db.commit()
    await db.refresh(job)

    # Dispatch Celery task
    run_replay_task.delay(str(job.id))

    traces_map = {t.id: t.input for t in traces}
    results = await db.execute(select(ReplayResult).where(ReplayResult.replay_job_id == job.id))
    return build_replay_job_out(job, results.scalars().all(), traces_map)


@router.post("/replay/{job_id}/stop")
async def stop_replay(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id, ReplayJob.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Replay job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Replay is not running")

    job.status = "stopped"

    # Mark remaining pending results as skipped
    pending_results = await db.execute(
        select(ReplayResult).where(
            ReplayResult.replay_job_id == job.id, ReplayResult.status == "pending"
        )
    )
    for r in pending_results.scalars().all():
        r.status = "skipped"

    await db.commit()
    return {"status": "stopped"}


@router.get("/replay/{job_id}", response_model=ReplayJobOut)
async def get_replay(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id, ReplayJob.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Replay job not found")

    results = await db.execute(select(ReplayResult).where(ReplayResult.replay_job_id == job.id))
    all_results = results.scalars().all()

    # Get trace inputs
    trace_ids = [r.trace_id for r in all_results]
    if trace_ids:
        traces_result = await db.execute(select(Trace).where(Trace.id.in_(trace_ids)))
        traces_map = {t.id: t.input for t in traces_result.scalars().all()}
    else:
        traces_map = {}

    return build_replay_job_out(job, all_results, traces_map)


@router.get("/replay/{job_id}/stream")
async def stream_replay(job_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    async def event_generator():
        last_completed = 0
        while True:
            async with async_session() as db:
                result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id))
                job = result.scalar_one_or_none()
                if not job:
                    yield {"event": "error", "data": json.dumps({"error": "Job not found"})}
                    return
                if job.user_id != current_user.id:
                    yield {"event": "error", "data": json.dumps({"error": "Job not found"})}
                    return

                results = await db.execute(
                    select(ReplayResult).where(ReplayResult.replay_job_id == job.id)
                )
                all_results = results.scalars().all()

                completed = [r for r in all_results if r.status in ("success", "failed")]
                if len(completed) > last_completed:
                    success_results = [r for r in completed if r.status == "success"]
                    improved = sum(
                        1 for r in success_results if r.score_delta and r.score_delta > 0
                    )
                    regressed = sum(
                        1 for r in success_results if r.score_delta and r.score_delta < 0
                    )
                    unchanged = sum(
                        1
                        for r in success_results
                        if r.score_delta is not None and r.score_delta == 0
                    )
                    failed_count = sum(1 for r in completed if r.status == "failed")

                    # Get the latest completed result
                    latest = completed[-1] if completed else None
                    latest_data = None
                    if latest:
                        latest_data = {
                            "trace_id": str(latest.trace_id),
                            "status": latest.status,
                            "score_delta": latest.score_delta,
                            "original_score": latest.original_score,
                            "replayed_score": latest.replayed_score,
                        }

                    yield {
                        "event": "progress",
                        "data": json.dumps(
                            {
                                "completed": len(completed),
                                "total": job.trace_count,
                                "improved": improved,
                                "unchanged": unchanged,
                                "regressed": regressed,
                                "failed": failed_count,
                                "latest": latest_data,
                            }
                        ),
                    }
                    last_completed = len(completed)

                if job.status in ("complete", "failed"):
                    success_results = [r for r in all_results if r.status == "success"]
                    improved = sum(
                        1 for r in success_results if r.score_delta and r.score_delta > 0
                    )
                    regressed = sum(
                        1 for r in success_results if r.score_delta and r.score_delta < 0
                    )
                    unchanged = sum(
                        1
                        for r in success_results
                        if r.score_delta is not None and r.score_delta == 0
                    )
                    failed_count = sum(1 for r in all_results if r.status == "failed")

                    yield {
                        "event": "done",
                        "data": json.dumps(
                            {
                                "improved": improved,
                                "unchanged": unchanged,
                                "regressed": regressed,
                                "failed": failed_count,
                            }
                        ),
                    }
                    return

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


@router.get("/replays", response_model=list[ReplayJobOut])
async def list_replays(
    prompt_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ReplayJob).where(ReplayJob.user_id == current_user.id).order_by(ReplayJob.created_at.desc())
    if prompt_id:
        query = query.where(ReplayJob.prompt_id == prompt_id)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Batch-fetch prompts and versions for enrichment
    prompt_ids = {j.prompt_id for j in jobs}
    version_ids = set()
    for j in jobs:
        version_ids.add(j.source_version_id)
        version_ids.add(j.target_version_id)

    prompt_map = {}
    if prompt_ids:
        p_result = await db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids)))
        prompt_map = {p.id: p.name for p in p_result.scalars().all()}

    version_map = {}
    if version_ids:
        v_result = await db.execute(select(PromptVersion).where(PromptVersion.id.in_(version_ids)))
        version_map = {v.id: v.version_number for v in v_result.scalars().all()}

    out = []
    for job in jobs:
        results = await db.execute(select(ReplayResult).where(ReplayResult.replay_job_id == job.id))
        all_results = results.scalars().all()

        trace_ids = [r.trace_id for r in all_results]
        traces_map = {}
        if trace_ids:
            traces_result = await db.execute(select(Trace).where(Trace.id.in_(trace_ids)))
            traces_map = {t.id: t.input for t in traces_result.scalars().all()}

        out.append(
            build_replay_job_out(
                job,
                all_results,
                traces_map,
                prompt_name=prompt_map.get(job.prompt_id, ""),
                source_version_number=version_map.get(job.source_version_id),
                target_version_number=version_map.get(job.target_version_id),
            )
        )

    return out


JUDGE_DISCUSS_SYSTEM = """You are the AI judge that evaluated a prompt change. Here is the context:

Original prompt (v{source_v}): {source_content}
Modified prompt (v{target_v}): {target_content}
User input: {user_input}
Original output (scored {original_score}/10): {original_output}
New output (scored {replayed_score}/10): {replayed_output}
Your reasoning: {judge_reasoning}

The user wants to discuss your evaluation. Be constructive and specific.
If they ask for prompt improvements, provide the complete improved prompt text.
When suggesting a prompt, wrap it in <suggested_prompt>...</suggested_prompt> tags."""


@router.post("/replay/{job_id}/results/{result_id}/discuss", response_model=JudgeDiscussResponse)
async def discuss_judge(
    job_id: uuid.UUID,
    result_id: uuid.UUID,
    body: JudgeDiscussRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="No API key configured.")

    # Fetch result, trace, and versions
    result = await db.execute(select(ReplayResult).where(ReplayResult.id == result_id))
    replay_result = result.scalar_one_or_none()
    if not replay_result:
        raise HTTPException(status_code=404, detail="Result not found")

    job_result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id, ReplayJob.user_id == current_user.id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    trace_result = await db.execute(select(Trace).where(Trace.id == replay_result.trace_id))
    trace = trace_result.scalar_one_or_none()

    source_v = await db.execute(select(PromptVersion).where(PromptVersion.id == job.source_version_id))
    source_version = source_v.scalar_one_or_none()
    target_v = await db.execute(select(PromptVersion).where(PromptVersion.id == job.target_version_id))
    target_version = target_v.scalar_one_or_none()

    # Extract user input from trace
    user_input = ""
    if trace:
        messages = trace.input.get("messages", [])
        user_input = next((m["content"] for m in messages if m["role"] == "user"), "")

    system_prompt = JUDGE_DISCUSS_SYSTEM.format(
        source_v=source_version.version_number if source_version else "?",
        source_content=source_version.content if source_version else "",
        target_v=target_version.version_number if target_version else "?",
        target_content=target_version.content if target_version else "",
        user_input=user_input,
        original_output=replay_result.original_output,
        original_score=replay_result.original_score or 0,
        replayed_output=replay_result.replayed_output,
        replayed_score=replay_result.replayed_score or 0,
        judge_reasoning=replay_result.judge_reasoning,
    )

    llm_messages = [{"role": "system", "content": system_prompt}, *body.messages]

    response_text = await asyncio.to_thread(
        call_llm, llm_messages, model=settings.judge_model, temperature=0.3, max_tokens=2048
    )

    # Parse suggested prompt
    suggested_prompt = None
    match = re.search(r"<suggested_prompt>(.*?)</suggested_prompt>", response_text, re.DOTALL)
    if match:
        suggested_prompt = match.group(1).strip()

    return JudgeDiscussResponse(response=response_text, suggested_prompt=suggested_prompt)


@router.post("/replay/{job_id}/results/{result_id}/rerun", response_model=RerunTraceResponse)
async def rerun_trace(
    job_id: uuid.UUID,
    result_id: uuid.UUID,
    body: RerunTraceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="No API key configured.")

    # Verify job belongs to user
    job_result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id, ReplayJob.user_id == current_user.id))
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Replay job not found")

    # Fetch the original result and trace
    result = await db.execute(select(ReplayResult).where(ReplayResult.id == result_id))
    replay_result = result.scalar_one_or_none()
    if not replay_result:
        raise HTTPException(status_code=404, detail="Result not found")

    trace_result = await db.execute(select(Trace).where(Trace.id == replay_result.trace_id))
    trace = trace_result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Extract user message and template vars from trace
    input_data = trace.input
    messages = input_data.get("messages", [])
    template_vars = input_data.get("template_vars", {})
    user_input = next((m["content"] for m in messages if m["role"] == "user"), "")

    # Render new prompt with template vars
    try:
        rendered = Template(body.prompt_content).render(**template_vars)
    except Exception:
        rendered = body.prompt_content

    model_config = body.model_config_data or {}
    model = model_config.get("model", settings.default_replay_model)
    temperature = model_config.get("temperature", 0.7)
    max_tokens = model_config.get("max_tokens", 1024)

    # Call LLM with new prompt
    new_messages = [
        {"role": "system", "content": rendered},
        {"role": "user", "content": user_input},
    ]
    replayed_output = await asyncio.to_thread(
        call_llm, new_messages, model=model, temperature=temperature, max_tokens=max_tokens
    )

    # Run judge
    judge_result = await asyncio.to_thread(
        run_judge, rendered, user_input, trace.output, replayed_output
    )

    return RerunTraceResponse(
        original_output=trace.output,
        replayed_output=replayed_output,
        original_score=judge_result["original_score"],
        replayed_score=judge_result["replayed_score"],
        score_delta=judge_result["replayed_score"] - judge_result["original_score"],
        judge_reasoning=judge_result["reasoning"],
    )
