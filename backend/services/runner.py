"""Pipeline runner with per-step checkpointing, resume, and event emission.

The runner:
1. Accepts a run_id and a list of step definitions.
2. Creates StepRun records for each step (or reuses existing ones on resume).
3. Executes each step sequentially, updating status in the DB.
4. On resume, skips completed/skipped steps and re-runs failed or pending ones.
5. On failure, marks the step as failed and stops — a subsequent call
   with the same run_id resumes from the first non-completed step.
6. Persists events to the run_events table so the API process can stream
   them over WebSocket (cross-container safe).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Coroutine

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RunStatus, StepStatus
from backend.db.repositories import (
    ArtifactRepository,
    RunEventRepository,
    RunRepository,
    StepRunRepository,
)
from backend.services.storage import ensure_run_dirs

logger = logging.getLogger(__name__)

# Steps in these statuses are skipped on resume — everything else is (re-)executed.
_SKIP_STATUSES = frozenset({StepStatus.COMPLETED, StepStatus.SKIPPED})


@dataclass
class StepDefinition:
    """Declares a pipeline step before execution."""

    module: str
    step_name: str
    execute: Callable[..., Coroutine[Any, Any, None]]
    """Async callable: execute(step_run_id, context) -> None.
    Should write artifacts and call ArtifactRepository to register them.
    Raise on failure — the runner catches and records the error."""


@dataclass
class RunContext:
    """Shared state passed to every step's execute function."""

    case_id: int
    run_id: int
    db: AsyncSession
    artifact_repo: ArtifactRepository
    config: dict


class PipelineRunner:
    """Executes a sequence of steps with per-step checkpointing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.run_repo = RunRepository(db)
        self.step_repo = StepRunRepository(db)
        self.artifact_repo = ArtifactRepository(db)
        self.event_repo = RunEventRepository(db)

    async def execute(
        self,
        case_id: int,
        run_id: int,
        steps: list[StepDefinition],
        config: dict | None = None,
    ) -> bool:
        """Run all steps for a given run. Returns True if all completed.

        On resume, completed/skipped steps are skipped. Failed and pending
        steps are (re-)executed. Execution stops at the first failure.
        """
        run = await self.run_repo.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        ensure_run_dirs(case_id, run_id)

        now = datetime.utcnow()
        # Only set started_at on the first invocation; preserve it on resume.
        # Always clear completed_at so a running run doesn't carry a stale timestamp.
        await self.run_repo.update(
            run_id,
            status=RunStatus.RUNNING.value,
            started_at=now if run.started_at is None else run.started_at,
            completed_at=None,
        )
        await self._emit_safe(run_id, "run_started")

        # Ensure StepRun records exist for every declared step
        existing_steps = await self.step_repo.list_by_run(run_id)
        existing_by_name = {(s.module, s.step_name): s for s in existing_steps}

        step_records = []
        for defn in steps:
            key = (defn.module, defn.step_name)
            if key in existing_by_name:
                step_records.append((defn, existing_by_name[key]))
            else:
                record = await self.step_repo.create(
                    run_id=run_id, module=defn.module, step_name=defn.step_name
                )
                step_records.append((defn, record))

        ctx = RunContext(
            case_id=case_id,
            run_id=run_id,
            db=self.db,
            artifact_repo=self.artifact_repo,
            config=config or {},
        )

        all_ok = True
        for defn, record in step_records:
            if record.status in _SKIP_STATUSES:
                logger.info(
                    "Skipping step %s/%s (already %s)",
                    defn.module, defn.step_name, record.status.value,
                )
                continue

            logger.info(
                "Running step %s/%s (step_run_id=%d)",
                defn.module, defn.step_name, record.id,
            )
            await self.step_repo.mark_running(record.id)
            await self._emit_safe(
                run_id, "step_started",
                step_run_id=record.id, module=defn.module, step_name=defn.step_name,
            )

            # Try/except covers ONLY the step's execute — event emission
            # is observational and must not affect step outcome.
            step_error: str | None = None
            try:
                await defn.execute(record.id, ctx)
            except Exception as exc:
                step_error = f"{type(exc).__name__}: {exc}"

            if step_error is None:
                await self.step_repo.mark_completed(record.id)
                logger.info("Step %s/%s completed", defn.module, defn.step_name)
                await self._emit_safe(
                    run_id, "step_completed",
                    step_run_id=record.id, module=defn.module, step_name=defn.step_name,
                )
            else:
                await self.step_repo.mark_failed(record.id, step_error)
                logger.error("Step %s/%s failed: %s", defn.module, defn.step_name, step_error)
                await self._emit_safe(
                    run_id, "step_failed",
                    step_run_id=record.id, module=defn.module,
                    step_name=defn.step_name, error_message=step_error,
                )
                all_ok = False
                break

        finished_at = datetime.utcnow()
        if all_ok:
            await self.run_repo.update(
                run_id, status=RunStatus.COMPLETED.value, completed_at=finished_at
            )
            await self._emit_safe(run_id, "run_completed")
        else:
            await self.run_repo.update(
                run_id, status=RunStatus.FAILED.value, completed_at=finished_at
            )
            await self._emit_safe(run_id, "run_failed")

        return all_ok

    async def _emit_safe(
        self,
        run_id: int,
        event_type: str,
        step_run_id: int | None = None,
        module: str | None = None,
        step_name: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Persist a run event to the database. Failures are logged, never raised.

        Event emission is observational — it must not change execution outcome.
        """
        try:
            await self.event_repo.insert(
                run_id=run_id,
                event_type=event_type,
                step_run_id=step_run_id,
                module=module,
                step_name=step_name,
                error_message=error_message,
            )
        except Exception:
            logger.warning(
                "Failed to emit event %s for run %d (non-fatal)", event_type, run_id,
                exc_info=True,
            )
