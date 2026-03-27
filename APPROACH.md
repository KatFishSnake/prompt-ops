# APPROACH.md — PromptOps

## What I Built

**PromptOps** is a prompt management and replay platform for production AI systems. It solves a specific problem: changing a prompt in production is high-anxiety because teams don't know if a tweak that fixes one edge case breaks five others.

The core loop: **version → replay → compare → promote**.

1. **Version prompts** with full history and model config (model, temperature, max_tokens)
2. **Ingest production traces** — real user inputs and LLM outputs
3. **Replay traces against a new prompt version** — send the same inputs through the new prompt and see what changes
4. **Compare side-by-side** — sentence-level diffs with LLM-as-judge scoring (original vs. replayed)
5. **Promote with confidence** — one click to make the new version active

This is the shadow deploy pattern from traditional infrastructure, applied to LLM prompts.

## Key Decisions

**Problem choice (#3 — Managing Prompt & Model Behavior):** I chose this because I've felt the pain of deploying prompt changes blind. The competitive landscape (Langfuse, Braintrust, Promptfoo) has gaps — nobody does the full loop of version → replay against real traffic → deploy in a lightweight, self-hosted package.

**Replay as the hero feature:** The "time-travel" moment is the differentiator. You take 20 real production traces, replay them against a draft prompt, and instantly see: 4 improved, 15 unchanged, 1 regressed. Side-by-side diffs show exactly what changed. One click to promote. This is the feature I protected above all others.

**Stack choices:**
- **FastAPI + Celery + Postgres + Redis** for the backend. Celery handles async replay fan-out (one task per trace). Postgres stores everything with proper relational integrity. Redis as Celery broker.
- **Next.js + Tailwind** for the frontend. Thin client — all business logic is server-side.
- **5-service docker-compose** — frontend, backend, worker, postgres, redis. One command to run everything.

**Seed data with pre-computed results:** The seed script populates 3 sample prompts, 20 traces, and a completed replay with pre-computed LLM judge scores. The reviewer sees a working product with real data on first `docker compose up` — no API keys required for the first impression.

**LLM-as-judge scoring:** Default judge model is gpt-4o-mini at temperature=0. A/B position is randomized per trace to mitigate positional bias. Judge JSON parsing has a fallback for malformed responses.

**Brutalist Blueprint design:** Zero border-radius everywhere. IBM Plex Mono for headings/data, IBM Plex Sans for body. Muted saturation. This is an intentional aesthetic choice to differentiate from every other LLM ops tool that uses cool grays + rounded corners.

## What I Intentionally Left Out

- **Auth/multi-tenant:** Single-tenant, local-only. No API keys on endpoints.
- **Pagination:** MVP returns all rows. Fine for demo-scale data.
- **Delete/archive:** Version history is the rollback mechanism.
- **Dark mode:** Deferred. Invested the time in replay instead.
- **Mobile responsive:** Desktop-only tool. Shows "Best on desktop" on small screens.
- **Standalone eval suites:** MVP evals happen through the replay system. Replay IS the eval.
- **Multi-turn conversations:** Single-turn only (one system + one user message per trace).

## What Breaks First Under Pressure

1. **No pagination** — list endpoints return all rows. At 10K+ traces, the API and UI will struggle.
2. **No rate limiting on replay** — a replay of 1000 traces would hammer the LLM API. The 5-concurrent limit helps but isn't enough for very large replays.
3. **SSE replaced with polling** — for simplicity, the frontend polls every 2s instead of using true SSE. This is adequate for 20-trace replays but would be chatty at scale.
4. **Single Celery worker** — one worker process with 5 concurrent threads. Multiple workers would be needed for production throughput.
5. **No trace sampling** — replays use ALL traces for a prompt. At scale, you'd want date-range filters or random sampling.

## What I'd Build Next

1. **Trace sampling & date filters** — select which traces to replay instead of all-or-nothing
2. **Eval datasets** — curated test sets independent of production traces
3. **A/B deployment** — route a percentage of traffic to a new version and compare live metrics
4. **The Proxy** — a drop-in proxy that sits between your app and the LLM API, automatically captures traces, serves the active prompt version, and enables hot-swapping without deploys
5. **Custom scoring plugins** — regex matchers, custom Python functions, not just LLM-as-judge

## Setup

```bash
# Clone the repo
git clone <repo-url> && cd <repo>

# Copy env file (OPENAI_API_KEY optional — seed data works without it)
cp .env.example .env

# Start everything
docker compose up --build
```

### Local
Frontend: http://localhost:3000
Backend API: http://localhost:8000
Health check: http://localhost:8000/health

### Live Deploy
Frontend (Vercel): https://prompt-ops-katfishsnakes-projects.vercel.app
Backend API (Railway): https://backend-production-fa0f.up.railway.app
Health check: https://backend-production-fa0f.up.railway.app/health

Note: Railway/Vercel URLs may become unavailable after the review period.

The app seeds itself on first boot with sample prompts, traces, and a completed replay. The onboarding flow guides you to the replay results immediately.
