from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import prompts, replay, scenarios, traces

app = FastAPI(title="PromptOps API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompts.router, prefix="/api")
app.include_router(traces.router, prefix="/api")
app.include_router(replay.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
