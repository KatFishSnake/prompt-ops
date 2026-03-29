import json
import random
import uuid
from datetime import UTC, datetime

import openai
from jinja2 import Template
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .celery_app import celery
from .config import settings
from .models import PromptVersion, ReplayJob, ReplayResult, ScenarioJob, ScenarioJobItem, Trace

# Sync engine for Celery tasks
sync_engine = create_engine(settings.database_url_sync)
SyncSession = sessionmaker(sync_engine)

JUDGE_PROMPT = """You are evaluating two AI assistant responses to the same user input.

System prompt context: {system_prompt}
User input: {user_input}

Response A: {response_a}
Response B: {response_b}

Score each response 1-10 on helpfulness, accuracy, and tone given the system prompt's intended behavior.
Return JSON: {{"score_a": N, "score_b": N, "reasoning": "..."}}"""


def call_llm(
    messages: list[dict], model: str, temperature: float = 0, max_tokens: int = 1024
) -> str:
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=settings.replay_timeout,
    )
    return response.choices[0].message.content


def run_judge(
    system_prompt: str, user_input: str, original_output: str, replayed_output: str
) -> dict:
    # Randomize A/B position to mitigate positional bias
    swap = random.random() > 0.5
    if swap:
        response_a, response_b = replayed_output, original_output
    else:
        response_a, response_b = original_output, replayed_output

    prompt = JUDGE_PROMPT.format(
        system_prompt=system_prompt,
        user_input=user_input,
        response_a=response_a,
        response_b=response_b,
    )

    result_text = call_llm(
        [{"role": "user", "content": prompt}],
        model=settings.judge_model,
        temperature=0,
    )

    try:
        # Strip markdown code fences if present (```json ... ```)
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        result = json.loads(cleaned)
        score_a = float(result["score_a"])
        score_b = float(result["score_b"])
        reasoning = result.get("reasoning", "")

        if swap:
            return {
                "original_score": score_b,
                "replayed_score": score_a,
                "reasoning": reasoning,
            }
        else:
            return {
                "original_score": score_a,
                "replayed_score": score_b,
                "reasoning": reasoning,
            }
    except (json.JSONDecodeError, KeyError, ValueError):
        return {
            "original_score": 0,
            "replayed_score": 0,
            "reasoning": f"Judge returned invalid response. Raw output: {result_text[:500]}",
        }


@celery.task(name="run_scenarios")
def run_scenarios_task(job_id: str):
    with SyncSession() as db:
        job = db.execute(select(ScenarioJob).where(ScenarioJob.id == uuid.UUID(job_id))).scalar_one()
        job.status = "running"
        db.commit()

        # Get active version template
        version = db.execute(
            select(PromptVersion).where(PromptVersion.id == job.prompt_version_id)
        ).scalar_one()

        # Get model config
        model_config = version.model_config_json or {}
        model = model_config.get("model", settings.default_replay_model)
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("max_tokens", 1024)

        # Get pending items
        items = (
            db.execute(
                select(ScenarioJobItem).where(
                    ScenarioJobItem.scenario_job_id == job.id,
                    ScenarioJobItem.status == "pending",
                )
            )
            .scalars()
            .all()
        )

        for item in items:
            try:
                item.status = "running"
                db.commit()

                # Render template with variables
                try:
                    rendered = Template(version.content).render(**item.variables_json)
                except Exception:
                    rendered = version.content

                # Build messages: system = rendered template, user = scenario message
                messages = [
                    {"role": "system", "content": rendered},
                    {"role": "user", "content": item.message},
                ]

                # Call LLM
                import time
                start = time.time()
                output = call_llm(messages, model=model, temperature=temperature, max_tokens=max_tokens)
                latency_ms = int((time.time() - start) * 1000)

                # Save as a real Trace (replay-compatible format)
                trace = Trace(
                    prompt_id=job.prompt_id,
                    prompt_version_id=job.prompt_version_id,
                    input={
                        "messages": messages,
                        "template_vars": item.variables_json,
                    },
                    output=output,
                    model=model,
                    latency_ms=latency_ms,
                    metadata_json={"source": "scenario_builder", "role": item.role},
                )
                db.add(trace)
                db.flush()

                item.trace_id = trace.id
                item.output_preview = output[:500] if output else ""
                item.latency_ms = latency_ms
                item.status = "success"
                item.completed_at = datetime.now(UTC)

            except Exception as e:
                item.status = "failed"
                item.error = str(e)[:1000]
                item.completed_at = datetime.now(UTC)

            db.commit()

        job.status = "complete"
        job.completed_at = datetime.now(UTC)
        db.commit()


@celery.task(name="run_replay")
def run_replay_task(job_id: str):
    with SyncSession() as db:
        job = db.execute(select(ReplayJob).where(ReplayJob.id == uuid.UUID(job_id))).scalar_one()
        job.status = "running"
        db.commit()

        # Get target version template
        target_version = db.execute(
            select(PromptVersion).where(PromptVersion.id == job.target_version_id)
        ).scalar_one()

        # Get all pending results
        results = (
            db.execute(
                select(ReplayResult).where(
                    ReplayResult.replay_job_id == job.id,
                    ReplayResult.status == "pending",
                )
            )
            .scalars()
            .all()
        )

        for result in results:
            # Check if user stopped the replay
            db.refresh(job)
            if job.status == "stopped":
                break

            try:
                trace = db.execute(select(Trace).where(Trace.id == result.trace_id)).scalar_one()

                # Extract input data
                input_data = trace.input
                messages = input_data.get("messages", [])
                template_vars = input_data.get("template_vars", {})

                # Render target template with Jinja2
                try:
                    rendered = Template(target_version.content).render(**template_vars)
                except Exception:
                    rendered = target_version.content

                # Build new messages: replace system message, keep user message
                new_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        new_messages.append({"role": "system", "content": rendered})
                    else:
                        new_messages.append(msg)

                # If no system message was found, prepend the rendered template
                if not any(m["role"] == "system" for m in new_messages):
                    new_messages.insert(0, {"role": "system", "content": rendered})

                # Get model config
                model_config = target_version.model_config_json or {}
                model = model_config.get("model", settings.default_replay_model)
                temperature = model_config.get("temperature", 0)
                max_tokens = model_config.get("max_tokens", 1024)

                # Call LLM
                replayed_output = call_llm(
                    new_messages, model=model, temperature=temperature, max_tokens=max_tokens
                )

                # Extract system prompt and user input for judge
                system_prompt = rendered
                user_input = next((m["content"] for m in messages if m["role"] == "user"), "")

                # Run judge
                judge_result = run_judge(system_prompt, user_input, trace.output, replayed_output)

                result.replayed_output = replayed_output
                result.original_score = judge_result["original_score"]
                result.replayed_score = judge_result["replayed_score"]
                result.score_delta = judge_result["replayed_score"] - judge_result["original_score"]
                result.judge_reasoning = judge_result["reasoning"]
                result.status = "success"
                result.completed_at = datetime.now(UTC)

            except Exception as e:
                result.status = "failed"
                result.error = str(e)[:1000]
                result.completed_at = datetime.now(UTC)

            db.commit()

        # Only mark complete if not stopped by user
        if job.status != "stopped":
            job.status = "complete"
            job.completed_at = datetime.now(UTC)
            db.commit()
