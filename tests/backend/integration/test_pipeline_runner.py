"""Integration tests for the pipeline runner with checkpoint/resume."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import (
    CaseRepository,
    RunRepository,
    StepRunRepository,
)
from backend.services.runner import PipelineRunner, RunContext, StepDefinition


async def _succeeding_step(step_run_id: int, ctx: RunContext) -> None:
    """A step that always succeeds."""
    pass


async def _failing_step(step_run_id: int, ctx: RunContext) -> None:
    """A step that always fails."""
    raise RuntimeError("Simulated failure")


async def _artifact_step(step_run_id: int, ctx: RunContext) -> None:
    """A step that registers an artifact."""
    await ctx.artifact_repo.create(
        step_run_id=step_run_id,
        artifact_type="test_output",
        fmt="json",
        path=f"/tmp/test_{step_run_id}.json",
    )


def _make_steps(
    count: int = 3, fail_at: int | None = None
) -> list[StepDefinition]:
    """Build a list of step definitions, optionally failing at a given index."""
    steps = []
    for i in range(count):
        if fail_at is not None and i == fail_at:
            steps.append(StepDefinition(
                module="test", step_name=f"step_{i}", execute=_failing_step
            ))
        else:
            steps.append(StepDefinition(
                module="test", step_name=f"step_{i}", execute=_succeeding_step
            ))
    return steps


@pytest.mark.asyncio
async def test_all_steps_complete(db_session: AsyncSession):
    """All steps succeed -> run status is completed with timestamps."""
    case_repo = CaseRepository(db_session)
    run_repo = RunRepository(db_session)

    case = await case_repo.create("Test Case")
    run = await run_repo.create(case.id)

    runner = PipelineRunner(db_session)
    result = await runner.execute(case.id, run.id, _make_steps(3))

    assert result is True

    updated_run = await run_repo.get(run.id)
    assert updated_run.status.value == "completed"
    assert updated_run.started_at is not None
    assert updated_run.completed_at is not None
    assert updated_run.completed_at >= updated_run.started_at

    step_repo = StepRunRepository(db_session)
    steps = await step_repo.list_by_run(run.id)
    assert len(steps) == 3
    assert all(s.status.value == "completed" for s in steps)


@pytest.mark.asyncio
async def test_failure_stops_execution(db_session: AsyncSession):
    """A failing step stops execution and marks the run as failed with timestamps."""
    case_repo = CaseRepository(db_session)
    run_repo = RunRepository(db_session)

    case = await case_repo.create("Fail Case")
    run = await run_repo.create(case.id)

    runner = PipelineRunner(db_session)
    result = await runner.execute(case.id, run.id, _make_steps(3, fail_at=1))

    assert result is False

    updated_run = await run_repo.get(run.id)
    assert updated_run.status.value == "failed"
    assert updated_run.started_at is not None
    assert updated_run.completed_at is not None

    step_repo = StepRunRepository(db_session)
    steps = await step_repo.list_by_run(run.id)
    assert steps[0].status.value == "completed"
    assert steps[1].status.value == "failed"
    assert "Simulated failure" in steps[1].error_message
    # Step 2 was never reached
    assert steps[2].status.value == "pending"


@pytest.mark.asyncio
async def test_checkpoint_resume_retries_failed(db_session: AsyncSession):
    """After a failure, re-running with fixed steps skips completed and retries failed+pending.

    The runner re-executes any step that is not completed or skipped.
    No manual state mutation is needed — the runner handles failed steps.
    """
    case_repo = CaseRepository(db_session)
    run_repo = RunRepository(db_session)

    case = await case_repo.create("Resume Case")
    run = await run_repo.create(case.id)

    # First run: step_0 ok, step_1 fails, step_2 never reached
    runner = PipelineRunner(db_session)
    await runner.execute(case.id, run.id, _make_steps(3, fail_at=1))

    run_after_fail = await run_repo.get(run.id)
    original_started_at = run_after_fail.started_at
    assert original_started_at is not None
    assert run_after_fail.completed_at is not None  # failure still sets completed_at

    step_repo = StepRunRepository(db_session)
    steps_before = await step_repo.list_by_run(run.id)
    assert steps_before[0].status.value == "completed"
    assert steps_before[1].status.value == "failed"
    assert steps_before[1].error_message is not None
    assert steps_before[2].status.value == "pending"

    # Resume with all-succeeding steps — the runner should:
    # - skip step_0 (completed)
    # - re-run step_1 (failed -> now succeeds)
    # - run step_2 (pending)
    # - preserve original started_at, clear and re-set completed_at
    all_succeed = _make_steps(3)
    result = await runner.execute(case.id, run.id, all_succeed)

    assert result is True

    steps_after = await step_repo.list_by_run(run.id)
    assert all(s.status.value == "completed" for s in steps_after)
    # mark_running should have cleared the error from the first attempt
    assert steps_after[1].error_message is None

    updated_run = await run_repo.get(run.id)
    assert updated_run.status.value == "completed"
    # started_at preserved from first invocation
    assert updated_run.started_at == original_started_at
    # completed_at is fresh (from the resume, not from the failure)
    assert updated_run.completed_at is not None
    assert updated_run.completed_at >= original_started_at


@pytest.mark.asyncio
async def test_run_timestamps_set(db_session: AsyncSession):
    """Verify started_at and completed_at are persisted on the AnalysisRun."""
    case = await CaseRepository(db_session).create("Timestamp Case")
    run = await RunRepository(db_session).create(case.id)

    assert run.started_at is None
    assert run.completed_at is None

    runner = PipelineRunner(db_session)
    await runner.execute(case.id, run.id, _make_steps(1))

    updated = await RunRepository(db_session).get(run.id)
    assert updated.started_at is not None
    assert updated.completed_at is not None
