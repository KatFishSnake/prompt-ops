# APPROACH.md — PromptOps

## What I Built

**PromptOps** is a prompt management and replay platform for production AI systems. It solves a specific problem: changing a prompt in production is high-anxiety because teams don't know if a tweak that fixes one edge case breaks five others.

The core loop: **version → generate scenarios → replay → compare → promote**.

1. **Version prompts** with full history, model config, and autosave
2. **Generate test scenarios with AI** — describe your use case, get diverse test scenarios, run them to create real traces
3. **Replay traces against a new prompt version** — send the same inputs through the new prompt and see what changes
4. **Compare side-by-side** — sentence-level diffs with LLM-as-judge scoring (original vs. replayed)
5. **Talk to the judge** — discuss the evaluation, get prompt improvement suggestions, rerun individual traces inline
6. **Promote with confidence** — one click to make the new version active

This is the shadow deploy pattern from traditional infrastructure, applied to LLM prompts.

## Key Decisions

**Problem choice (#3 — Managing Prompt & Model Behavior):** I chose this because I've felt the pain of deploying prompt changes blind. The competitive landscape (Langfuse, Braintrust, Promptfoo) has gaps — nobody does the full loop of version → replay against real traffic → deploy in a lightweight, self-hosted package. More importantly, nobody lets you generate test data and evaluate within the same tool.

**Self-contained eval loop (the differentiator):** Every competing tool requires external integration before you can evaluate anything. Promptfoo needs YAML configs. Braintrust needs SDK integration. Langfuse needs trace instrumentation. PromptOps generates its own test data via AI-powered scenario generation. A reviewer opens the app, describes a use case, and the full evaluate loop plays out in the browser. Zero external setup.

**Replay as the hero feature:** The "time-travel" moment. You generate traces, edit the prompt, replay them against the new version, and instantly see: which improved, which stayed the same, which regressed. Side-by-side diffs show exactly what changed. Judge scores tell you why. This is the feature I protected above all others.

**Interactive judge chat:** After a replay, you can discuss any result with the judge. Ask why it scored the way it did, get a prompt improvement suggestion, rerun a single trace inline to test it, or create a new version and replay all traces. The full feedback loop happens in one place.

**Magic link auth + multi-user isolation:** Passwordless login via Resend. Each user gets their own workspace with isolated prompts, traces, and replays. API keys for integration endpoints. Demo prompts seeded on first login.

**Stack choices:**
- **FastAPI + Celery + Postgres + Redis** for the backend. Celery handles async replay and scenario fan-out. Redis as Celery broker AND magic link token store.
- **Next.js + Tailwind** for the frontend. Thin client — all business logic is server-side.
- **5-service docker-compose** — frontend, backend, worker, postgres, redis. One command to run everything.

**Autosave + mutable versions:** Prompt edits auto-save after 3 seconds of inactivity (updates the version in-place, no version spam). "Replay vs Active" always uses the latest content. Creating a new version is an explicit action via "+ New Version".

**LLM-as-judge scoring:** Default judge model is gpt-4o-mini at temperature=0. A/B position is randomized per trace to mitigate positional bias. Judge JSON parsing has a fallback for malformed responses.

**Brutalist Blueprint design:** Zero border-radius everywhere. IBM Plex Mono for headings/data, IBM Plex Sans for body. Muted saturation. This is an intentional aesthetic choice to differentiate from every other LLM ops tool.

## What I Intentionally Left Out

- **Pagination:** MVP returns all rows. Fine for demo-scale data.
- **Dark mode:** Deferred. Invested the time in replay and judge chat instead.
- **Mobile responsive:** Desktop-only tool.
- **Standalone eval suites:** MVP evals happen through the replay system. Replay IS the eval.
- **Multi-turn conversations:** Single-turn only (one system + one user message per trace).
- **JWT refresh tokens:** 7-day expiry is fine for a demo. No refresh flow needed.
- **API key rotation:** Keys are generated on signup and shown in the Integration panel. No regeneration UI yet.

## What Breaks First Under Pressure

1. **No pagination** — list endpoints return all rows. At 10K+ traces, the API and UI will struggle.
2. **No rate limiting on replay** — a replay of 1000 traces would hammer the LLM API. The 5-concurrent limit helps but isn't enough for very large replays.
3. **Polling instead of SSE** — the frontend polls every 2s instead of using true SSE. Adequate for small replays but chatty at scale.
4. **Single Celery worker** — one worker process with 5 concurrent threads. Multiple workers would be needed for production throughput.
5. **No trace sampling** — replays use ALL traces for a prompt. At scale, you'd want date-range filters or random sampling.

## What I'd Build Next

1. **Trace sampling & date filters** — select which traces to replay instead of all-or-nothing
2. **Eval datasets** — curated test sets independent of production traces
3. **Auto-generated scenarios from existing traces** — analyze production traffic to find edge cases
4. **A/B deployment** — route a percentage of traffic to a new version and compare live metrics
5. **The Proxy** — a drop-in proxy that sits between your app and the LLM API, automatically captures traces, serves the active prompt version, and enables hot-swapping without deploys
6. **Custom scoring plugins** — regex matchers, custom Python functions, not just LLM-as-judge

## Setup

```bash
# Clone the repo
git clone <repo-url> && cd <repo>

# Copy env file and fill in your keys
cp .env.example .env

# Start everything
docker compose up --build
```

On first boot, navigate to localhost:3000. You'll be prompted to log in via magic link (or use the dev bypass if `DEV_AUTH_EMAIL` is set). After login, 3 demo prompts are seeded in your workspace. The onboarding flow guides you through the product.

### Local
Frontend: http://localhost:3000
Backend API: http://localhost:8000
Health check: http://localhost:8000/health

### Live Deploy
Frontend: https://promptops.world
Backend API (Railway): https://backend-production-fa0f.up.railway.app
Health check: https://backend-production-fa0f.up.railway.app/health
