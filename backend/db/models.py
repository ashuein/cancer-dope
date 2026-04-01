"""SQLAlchemy ORM models for the canonical workflow and provenance model.

Entity chain: Case -> AnalysisRun -> StepRun -> Artifact -> VisualizationDataset
                                            -> ExternalCall
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------- Enums ----------


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    MISSING = "missing"


# ---------- Models ----------


class Case(Base):
    """Patient or project container."""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(255), nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    runs = relationship("AnalysisRun", back_populates="case", cascade="all, delete-orphan")


class AnalysisRun(Base):
    """One execution over a case."""

    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(RunStatus), default=RunStatus.PENDING, nullable=False)
    config_snapshot = Column(Text, default="{}")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    case = relationship("Case", back_populates="runs")
    steps = relationship("StepRun", back_populates="run", cascade="all, delete-orphan")
    visualization_datasets = relationship(
        "VisualizationDataset", back_populates="run", cascade="all, delete-orphan"
    )


class StepRun(Base):
    """Checkpointable unit of execution within a run."""

    __tablename__ = "step_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    module = Column(String(100), nullable=False)
    step_name = Column(String(255), nullable=False)
    status = Column(Enum(StepStatus), default=StepStatus.PENDING, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    run = relationship("AnalysisRun", back_populates="steps")
    artifacts = relationship("Artifact", back_populates="step_run", cascade="all, delete-orphan")
    external_calls = relationship(
        "ExternalCall", back_populates="step_run", cascade="all, delete-orphan"
    )


class Artifact(Base):
    """Versioned output file or dataset produced by a step."""

    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    step_run_id = Column(Integer, ForeignKey("step_runs.id", ondelete="CASCADE"), nullable=False)
    artifact_type = Column(String(100), nullable=False)
    format = Column(String(50), nullable=False)
    path = Column(Text, nullable=False)
    checksum = Column(String(64))
    size_bytes = Column(Integer)
    status = Column(Enum(ArtifactStatus), default=ArtifactStatus.PENDING, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    step_run = relationship("StepRun", back_populates="artifacts")


class VisualizationDataset(Base):
    """Frontend-ready data bundle derived from artifacts."""

    __tablename__ = "visualization_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    page = Column(String(100), nullable=False)
    source_artifact_ids = Column(Text, default="[]")
    path = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    run = relationship("AnalysisRun", back_populates="visualization_datasets")


class ExternalCall(Base):
    """Audit log entry for external API or subprocess calls."""

    __tablename__ = "external_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    step_run_id = Column(Integer, ForeignKey("step_runs.id", ondelete="CASCADE"), nullable=False)
    service = Column(String(100), nullable=False)
    request_summary = Column(Text)
    response_status = Column(Integer)
    latency_ms = Column(Float)
    called_at = Column(DateTime, server_default=func.now())

    step_run = relationship("StepRun", back_populates="external_calls")


class AlphaFoldJob(Base):
    """Tracks AlphaFold3 rate-limited job queue."""

    __tablename__ = "alphafold_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    step_run_id = Column(Integer, ForeignKey("step_runs.id", ondelete="SET NULL"))
    job_id = Column(String(255))
    status = Column(String(50), default="queued")
    submitted_at = Column(DateTime)
    completed_at = Column(DateTime)
    result_path = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class StructureCache(Base):
    """Cache of predicted or fetched protein structures."""

    __tablename__ = "structure_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_hash = Column(String(64), unique=True, nullable=False)
    source = Column(String(50), nullable=False)
    path = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_accessed = Column(DateTime, server_default=func.now())


class RunEvent(Base):
    """Persistent event log written by workers, streamed by the API over WebSocket.

    Workers INSERT rows here. The API WebSocket endpoint polls for new rows
    with id > last_seen_id. This bridges the container boundary without
    requiring an in-memory message broker.
    """

    __tablename__ = "run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_run_id = Column(Integer, ForeignKey("step_runs.id", ondelete="SET NULL"))
    event_type = Column(String(50), nullable=False)
    module = Column(String(100))
    step_name = Column(String(255))
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
