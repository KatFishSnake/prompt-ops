from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://promptops:promptops@postgres:5432/promptops"
    database_url_sync: str = "postgresql://promptops:promptops@postgres:5432/promptops"
    redis_url: str = "redis://redis:6379/0"
    openai_api_key: str = ""
    judge_model: str = "gpt-4o-mini"
    default_replay_model: str = "gpt-4o-mini"
    max_concurrent_replays: int = 5
    replay_timeout: int = 30
    replay_max_retries: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
