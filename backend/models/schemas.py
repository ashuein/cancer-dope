"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Valid status transitions for workflow entities
RunStatusLiteral = Literal["pending", "running", "completed", "failed", "cancelled"]


# ---------- Case ----------


class CaseCreate(BaseModel):
    label: str
    metadata_json: str = "{}"


class CaseUpdate(BaseModel):
    label: str | None = None
    metadata_json: str | None = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    metadata_json: str
    created_at: datetime
    updated_at: datetime


# ---------- AnalysisRun ----------


class RunCreate(BaseModel):
    config_snapshot: str = "{}"


class RunUpdate(BaseModel):
    status: RunStatusLiteral | None = None
    config_snapshot: str | None = None


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    status: str
    config_snapshot: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# ---------- StepRun ----------


class StepRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    module: str
    step_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


# ---------- Artifact ----------


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_run_id: int
    artifact_type: str
    format: str
    path: str
    checksum: str | None
    size_bytes: int | None
    status: str
    created_at: datetime


# ---------- VisualizationDataset ----------


class VisualizationDatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    case_id: int
    page: str
    source_artifact_ids: str
    path: str
    created_at: datetime


# ---------- ExternalCall ----------


class ExternalCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_run_id: int
    service: str
    request_summary: str | None
    response_status: int | None
    latency_ms: float | None
    called_at: datetime


# ---------- WebSocket ----------


class RunEvent(BaseModel):
    """Real-time event pushed over WebSocket during run execution."""

    run_id: int
    step_run_id: int | None = None
    event_type: Literal["run_started", "step_started", "step_completed", "step_failed", "run_completed", "run_failed"]
    module: str | None = None
    step_name: str | None = None
    error_message: str | None = None
    timestamp: datetime


# ---------- Health ----------


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ModuleStatus(BaseModel):
    name: str
    enabled: bool
