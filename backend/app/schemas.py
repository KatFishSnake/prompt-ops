from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# Prompt schemas
class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class PromptVersionCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    content: str = Field(..., min_length=1)
    model_config_json: dict = Field(default_factory=dict, alias="model_config")


class PromptVersionOut(BaseModel):
    id: UUID
    prompt_id: UUID
    version_number: int
    content: str
    model_config_json: dict
    is_active: bool
    created_at: datetime
    created_by: str

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class PromptOut(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    versions: list[PromptVersionOut] = []

    model_config = {"from_attributes": True}


class PromptListItem(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    active_version: int | None = None
    latest_replay: dict | None = None

    model_config = {"from_attributes": True}


class PromoteRequest(BaseModel):
    version_id: UUID


# Trace schemas
class TraceInput(BaseModel):
    prompt_name: str | None = None
    input: dict
    output: str
    model: str = ""
    latency_ms: int = 0
    metadata: dict = Field(default_factory=dict)


class TraceBatchInput(BaseModel):
    traces: list[TraceInput] = Field(..., max_length=100)


class TraceOut(BaseModel):
    id: UUID
    prompt_id: UUID | None
    prompt_version_id: UUID | None
    input: dict
    output: str
    model: str
    latency_ms: int
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# Replay schemas
class ReplayRequest(BaseModel):
    prompt_id: UUID
    source_version_id: UUID
    target_version_id: UUID


class ReplayResultOut(BaseModel):
    id: UUID
    replay_job_id: UUID
    trace_id: UUID
    status: str
    original_output: str
    replayed_output: str
    original_score: float | None
    replayed_score: float | None
    score_delta: float | None
    judge_reasoning: str
    error: str | None
    completed_at: datetime | None
    trace_input: dict | None = None

    model_config = {"from_attributes": True}


class ReplayJobOut(BaseModel):
    id: UUID
    prompt_id: UUID
    source_version_id: UUID
    target_version_id: UUID
    status: str
    trace_count: int
    created_at: datetime
    completed_at: datetime | None
    results: list[ReplayResultOut] = []
    improved: int = 0
    unchanged: int = 0
    regressed: int = 0
    failed: int = 0
    avg_original_score: float | None = None
    avg_replayed_score: float | None = None

    model_config = {"from_attributes": True}


# Serve schema
class ServeOut(BaseModel):
    prompt_name: str
    version_number: int
    content: str
    model_config_json: dict

    model_config = {"from_attributes": True, "protected_namespaces": ()}


# Playground schemas
class PlaygroundRequest(BaseModel):
    content: str = Field(..., min_length=1)
    variables: dict = Field(default_factory=dict)
    user_message: str = Field(..., min_length=1)
    model_config_data: dict = Field(default_factory=dict, alias="model_config")

    model_config = {"protected_namespaces": ()}


class PlaygroundResponse(BaseModel):
    output: str
    latency_ms: int
