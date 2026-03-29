from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import auth, prompts, replay, scenarios, traces

app = FastAPI(title="PromptOps API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(traces.router, prefix="/api")
app.include_router(replay.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    if settings.dev_auth_email:
        print(f"\n🔑 Dev login: {settings.frontend_url}/api/auth/dev-login\n")
