"""Data access layer — repository classes for core entities."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Sentinel for "explicitly set this field to None" vs "don't touch this field".
_UNSET: Any = object()

from backend.db.models import (
    AnalysisRun,
    Artifact,
    ArtifactStatus,
    Case,
    ExternalCall,
    RunEvent,
    StepRun,
    StepStatus,
    VisualizationDataset,
)


class CaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, label: str, metadata_json: str = "{}") -> Case:
        case = Case(label=label, metadata_json=metadata_json)
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        return case

    async def get(self, case_id: int) -> Case | None:
        return await self.db.get(Case, case_id)

    async def list_all(self) -> list[Case]:
        result = await self.db.execute(select(Case).order_by(Case.created_at.desc()))
        return list(result.scalars().all())

    async def update(
        self,
        case_id: int,
        label: str | None = None,
        metadata_json: str | None = None,
    ) -> Case | None:
        case = await self.db.get(Case, case_id)
        if not case:
            return None
        if label is not None:
            case.label = label
        if metadata_json is not None:
            case.metadata_json = metadata_json
        await self.db.commit()
        await self.db.refresh(case)
        return case

    async def delete(self, case_id: int) -> bool:
        case = await self.db.get(Case, case_id)
        if not case:
            return False
        await self.db.delete(case)
        await self.db.commit()
        return True


class RunRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: int, config_snapshot: str = "{}") -> AnalysisRun:
        run = AnalysisRun(case_id=case_id, config_snapshot=config_snapshot)
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def get(self, run_id: int, case_id: int | None = None) -> AnalysisRun | None:
        stmt = select(AnalysisRun).where(AnalysisRun.id == run_id)
        if case_id is not None:
            stmt = stmt.where(AnalysisRun.case_id == case_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_case(self, case_id: int) -> list[AnalysisRun]:
        result = await self.db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.case_id == case_id)
            .order_by(AnalysisRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self,
        run_id: int,
        status: str | None = None,
        config_snapshot: str | None = None,
        started_at: datetime | None | Any = _UNSET,
        completed_at: datetime | None | Any = _UNSET,
    ) -> AnalysisRun | None:
        run = await self.db.get(AnalysisRun, run_id)
        if not run:
            return None
        if status is not None:
            run.status = status
        if config_snapshot is not None:
            run.config_snapshot = config_snapshot
        if started_at is not _UNSET:
            run.started_at = started_at
        if completed_at is not _UNSET:
            run.completed_at = completed_at
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def delete(self, run_id: int) -> bool:
        run = await self.db.get(AnalysisRun, run_id)
        if not run:
            return False
        await self.db.delete(run)
        await self.db.commit()
        return True


class StepRunRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, run_id: int, module: str, step_name: str
    ) -> StepRun:
        step = StepRun(run_id=run_id, module=module, step_name=step_name)
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def get(self, step_id: int) -> StepRun | None:
        return await self.db.get(StepRun, step_id)

    async def list_by_run(self, run_id: int) -> list[StepRun]:
        result = await self.db.execute(
            select(StepRun).where(StepRun.run_id == run_id).order_by(StepRun.created_at)
        )
        return list(result.scalars().all())

    async def mark_running(self, step_id: int) -> StepRun | None:
        step = await self.db.get(StepRun, step_id)
        if not step:
            return None
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        step.completed_at = None
        step.error_message = None
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def mark_completed(self, step_id: int) -> StepRun | None:
        step = await self.db.get(StepRun, step_id)
        if not step:
            return None
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def mark_failed(self, step_id: int, error_message: str) -> StepRun | None:
        step = await self.db.get(StepRun, step_id)
        if not step:
            return None
        step.status = StepStatus.FAILED
        step.completed_at = datetime.utcnow()
        step.error_message = error_message
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def mark_skipped(self, step_id: int) -> StepRun | None:
        step = await self.db.get(StepRun, step_id)
        if not step:
            return None
        step.status = StepStatus.SKIPPED
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def first_pending(self, run_id: int) -> StepRun | None:
        """Return the earliest pending step for a run, or None if all are done."""
        result = await self.db.execute(
            select(StepRun)
            .where(StepRun.run_id == run_id, StepRun.status == StepStatus.PENDING)
            .order_by(StepRun.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()


class ArtifactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        step_run_id: int,
        artifact_type: str,
        fmt: str,
        path: str,
        checksum: str | None = None,
        size_bytes: int | None = None,
        status: ArtifactStatus = ArtifactStatus.PENDING,
    ) -> Artifact:
        artifact = Artifact(
            step_run_id=step_run_id,
            artifact_type=artifact_type,
            format=fmt,
            path=path,
            checksum=checksum,
            size_bytes=size_bytes,
            status=status,
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def get(self, artifact_id: int) -> Artifact | None:
        return await self.db.get(Artifact, artifact_id)

    async def list_by_step(self, step_run_id: int) -> list[Artifact]:
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.step_run_id == step_run_id)
            .order_by(Artifact.created_at)
        )
        return list(result.scalars().all())

    async def list_by_case(self, case_id: int) -> list[Artifact]:
        result = await self.db.execute(
            select(Artifact)
            .join(StepRun)
            .join(AnalysisRun)
            .where(AnalysisRun.case_id == case_id)
            .order_by(Artifact.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_ready(
        self, artifact_id: int, checksum: str, size_bytes: int
    ) -> Artifact | None:
        artifact = await self.db.get(Artifact, artifact_id)
        if not artifact:
            return None
        artifact.status = ArtifactStatus.READY
        artifact.checksum = checksum
        artifact.size_bytes = size_bytes
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def mark_failed(self, artifact_id: int) -> Artifact | None:
        artifact = await self.db.get(Artifact, artifact_id)
        if not artifact:
            return None
        artifact.status = ArtifactStatus.FAILED
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact


class VisualizationDatasetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        run_id: int,
        case_id: int,
        page: str,
        path: str,
        source_artifact_ids: str = "[]",
    ) -> VisualizationDataset:
        ds = VisualizationDataset(
            run_id=run_id,
            case_id=case_id,
            page=page,
            path=path,
            source_artifact_ids=source_artifact_ids,
        )
        self.db.add(ds)
        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def get(self, dataset_id: int) -> VisualizationDataset | None:
        return await self.db.get(VisualizationDataset, dataset_id)

    async def list_by_case(self, case_id: int) -> list[VisualizationDataset]:
        result = await self.db.execute(
            select(VisualizationDataset)
            .where(VisualizationDataset.case_id == case_id)
            .order_by(VisualizationDataset.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_page(self, case_id: int, page: str) -> VisualizationDataset | None:
        result = await self.db.execute(
            select(VisualizationDataset)
            .where(
                VisualizationDataset.case_id == case_id,
                VisualizationDataset.page == page,
            )
            .order_by(VisualizationDataset.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ExternalCallRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        step_run_id: int,
        service: str,
        request_summary: str | None = None,
        response_status: int | None = None,
        latency_ms: float | None = None,
    ) -> ExternalCall:
        call = ExternalCall(
            step_run_id=step_run_id,
            service=service,
            request_summary=request_summary,
            response_status=response_status,
            latency_ms=latency_ms,
        )
        self.db.add(call)
        await self.db.commit()
        await self.db.refresh(call)
        return call

    async def list_by_step(self, step_run_id: int) -> list[ExternalCall]:
        result = await self.db.execute(
            select(ExternalCall)
            .where(ExternalCall.step_run_id == step_run_id)
            .order_by(ExternalCall.called_at)
        )
        return list(result.scalars().all())


class RunEventRepository:
    """Persistent event log that bridges worker and API containers.

    Workers call insert() to record events.
    The API WebSocket endpoint calls poll_after() to stream new events.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert(
        self,
        run_id: int,
        event_type: str,
        step_run_id: int | None = None,
        module: str | None = None,
        step_name: str | None = None,
        error_message: str | None = None,
    ) -> RunEvent:
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            step_run_id=step_run_id,
            module=module,
            step_name=step_name,
            error_message=error_message,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def poll_after(self, run_id: int, after_id: int = 0, limit: int = 50) -> list[RunEvent]:
        """Return events for a run with id > after_id, ordered ascending."""
        result = await self.db.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.id > after_id)
            .order_by(RunEvent.id)
            .limit(limit)
        )
        return list(result.scalars().all())
