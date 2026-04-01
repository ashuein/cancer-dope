"""Tests for the DB-backed run event system."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import (
    CaseRepository,
    RunEventRepository,
    RunRepository,
    StepRunRepository,
)
from backend.services.runner import PipelineRunner, RunContext, StepDefinition


async def _noop_step(step_run_id: int, ctx: RunContext) -> None:
    pass


async def _fail_step(step_run_id: int, ctx: RunContext) -> None:
    raise ValueError("boom")


@pytest.mark.asyncio
async def test_successful_run_emits_events(db_session: AsyncSession):
    """A successful 2-step run should emit: run_started, 2x(step_started + step_completed), run_completed."""
    case = await CaseRepository(db_session).create("Event Case")
    run = await RunRepository(db_session).create(case.id)

    steps = [
        StepDefinition(module="m", step_name="s1", execute=_noop_step),
        StepDefinition(module="m", step_name="s2", execute=_noop_step),
    ]

    runner = PipelineRunner(db_session)
    await runner.execute(case.id, run.id, steps)

    repo = RunEventRepository(db_session)
    events = await repo.poll_after(run.id, after_id=0)

    types = [e.event_type for e in events]
    assert types == [
        "run_started",
        "step_started", "step_completed",
        "step_started", "step_completed",
        "run_completed",
    ]
    # All events belong to this run
    assert all(e.run_id == run.id for e in events)


@pytest.mark.asyncio
async def test_failed_run_emits_step_failed_and_run_failed(db_session: AsyncSession):
    """A run that fails at step 1 should emit step_failed and run_failed."""
    case = await CaseRepository(db_session).create("Fail Event Case")
    run = await RunRepository(db_session).create(case.id)

    steps = [
        StepDefinition(module="m", step_name="s1", execute=_noop_step),
        StepDefinition(module="m", step_name="s2", execute=_fail_step),
    ]

    runner = PipelineRunner(db_session)
    await runner.execute(case.id, run.id, steps)

    repo = RunEventRepository(db_session)
    events = await repo.poll_after(run.id, after_id=0)

    types = [e.event_type for e in events]
    assert types == [
        "run_started",
        "step_started", "step_completed",
        "step_started", "step_failed",
        "run_failed",
    ]

    failed_event = [e for e in events if e.event_type == "step_failed"][0]
    assert "boom" in failed_event.error_message
    assert failed_event.step_name == "s2"


@pytest.mark.asyncio
async def test_poll_after_returns_only_newer_events(db_session: AsyncSession):
    """poll_after with a cursor should return only events after that id."""
    case = await CaseRepository(db_session).create("Poll Case")
    run = await RunRepository(db_session).create(case.id)

    steps = [StepDefinition(module="m", step_name="s1", execute=_noop_step)]
    runner = PipelineRunner(db_session)
    await runner.execute(case.id, run.id, steps)

    repo = RunEventRepository(db_session)
    all_events = await repo.poll_after(run.id, after_id=0)
    assert len(all_events) >= 4  # run_started, step_started, step_completed, run_completed

    mid = all_events[1].id
    newer = await repo.poll_after(run.id, after_id=mid)
    assert all(e.id > mid for e in newer)
    assert len(newer) == len(all_events) - 2
