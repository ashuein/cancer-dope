"""Tests for partial-case handling — cases with missing modules or no artifacts."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import (
    CaseRepository,
    RunRepository,
    VisualizationDatasetRepository,
)


@pytest.mark.asyncio
async def test_case_with_no_runs(client: AsyncClient):
    """A case with no runs should return empty lists for runs and artifacts."""
    resp = await client.post("/cases", json={"label": "Empty Case"})
    case_id = resp.json()["id"]

    runs = await client.get(f"/cases/{case_id}/runs")
    assert runs.status_code == 200
    assert runs.json() == []

    artifacts = await client.get(f"/cases/{case_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json() == []


@pytest.mark.asyncio
async def test_case_with_run_but_no_steps(client: AsyncClient):
    """A case with a run but no steps should return empty step list."""
    case_resp = await client.post("/cases", json={"label": "No Steps Case"})
    case_id = case_resp.json()["id"]

    run_resp = await client.post(f"/cases/{case_id}/runs", json={})
    run_id = run_resp.json()["id"]

    steps = await client.get(f"/cases/{case_id}/runs/{run_id}/steps")
    assert steps.status_code == 200
    assert steps.json() == []


@pytest.mark.asyncio
async def test_vizdata_missing_page(db_session: AsyncSession):
    """Querying a visualization dataset for a page that hasn't been built returns None."""
    case = await CaseRepository(db_session).create("Partial Case")
    repo = VisualizationDatasetRepository(db_session)
    result = await repo.get_for_page(case.id, "timeline")
    assert result is None


@pytest.mark.asyncio
async def test_vizdata_exists_for_built_page(db_session: AsyncSession):
    """After building a dataset, it should be retrievable by page."""
    case = await CaseRepository(db_session).create("Built Case")
    run = await RunRepository(db_session).create(case.id)

    repo = VisualizationDatasetRepository(db_session)
    ds = await repo.create(
        run_id=run.id,
        case_id=case.id,
        page="timeline",
        path="/data/timeline.json",
        source_artifact_ids="[1, 2]",
    )
    assert ds.page == "timeline"

    fetched = await repo.get_for_page(case.id, "timeline")
    assert fetched is not None
    assert fetched.id == ds.id


@pytest.mark.asyncio
async def test_partial_case_some_pages_missing(db_session: AsyncSession):
    """A case may have some pages built and others not — each should be independently queryable."""
    case = await CaseRepository(db_session).create("Mixed Case")
    run = await RunRepository(db_session).create(case.id)
    repo = VisualizationDatasetRepository(db_session)

    # Build timeline but not track1
    await repo.create(
        run_id=run.id, case_id=case.id, page="timeline",
        path="/data/tl.json",
    )

    assert await repo.get_for_page(case.id, "timeline") is not None
    assert await repo.get_for_page(case.id, "track1") is None
    assert await repo.get_for_page(case.id, "gsea") is None
