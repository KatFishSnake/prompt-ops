import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..database import async_session, get_db
from ..models import Prompt, PromptVersion, ReplayJob, ReplayResult, Trace
from ..schemas import ReplayJobOut, ReplayRequest, ReplayResultOut
from ..tasks import run_replay_task

router = APIRouter()


def build_replay_job_out(
    job: ReplayJob, results: list[ReplayResult], traces_map: dict
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
    )


@router.post("/replay", response_model=ReplayJobOut)
async def start_replay(body: ReplayRequest, db: AsyncSession = Depends(get_db)):
    # Validate prompt and versions exist
    prompt = await db.execute(select(Prompt).where(Prompt.id == body.prompt_id))
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


@router.get("/replay/{job_id}", response_model=ReplayJobOut)
async def get_replay(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id))
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
async def stream_replay(job_id: uuid.UUID):
    async def event_generator():
        last_completed = 0
        while True:
            async with async_session() as db:
                result = await db.execute(select(ReplayJob).where(ReplayJob.id == job_id))
                job = result.scalar_one_or_none()
                if not job:
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
):
    query = select(ReplayJob).order_by(ReplayJob.created_at.desc())
    if prompt_id:
        query = query.where(ReplayJob.prompt_id == prompt_id)

    result = await db.execute(query)
    jobs = result.scalars().all()

    out = []
    for job in jobs:
        results = await db.execute(select(ReplayResult).where(ReplayResult.replay_job_id == job.id))
        all_results = results.scalars().all()

        trace_ids = [r.trace_id for r in all_results]
        traces_map = {}
        if trace_ids:
            traces_result = await db.execute(select(Trace).where(Trace.id.in_(trace_ids)))
            traces_map = {t.id: t.input for t in traces_result.scalars().all()}

        out.append(build_replay_job_out(job, all_results, traces_map))

    return out
