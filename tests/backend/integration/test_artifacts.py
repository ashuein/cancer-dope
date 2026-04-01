"""Integration tests for artifact registration, checksum, and download."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ArtifactStatus
from backend.db.repositories import (
    ArtifactRepository,
    CaseRepository,
    RunRepository,
    StepRunRepository,
)
from backend.services.storage import bytes_checksum, file_checksum


@pytest.mark.asyncio
async def test_artifact_create_and_mark_ready(db_session: AsyncSession):
    """Create an artifact, then mark it ready with checksum and size."""
    case = await CaseRepository(db_session).create("Art Case")
    run = await RunRepository(db_session).create(case.id)
    step = await StepRunRepository(db_session).create(run.id, "test", "step_a")

    repo = ArtifactRepository(db_session)
    art = await repo.create(
        step_run_id=step.id,
        artifact_type="track1_results_json",
        fmt="json",
        path="/tmp/results.json",
    )
    assert art.status == ArtifactStatus.PENDING

    updated = await repo.mark_ready(art.id, checksum="abc123", size_bytes=1024)
    assert updated.status == ArtifactStatus.READY
    assert updated.checksum == "abc123"
    assert updated.size_bytes == 1024


@pytest.mark.asyncio
async def test_artifact_mark_failed(db_session: AsyncSession):
    """Mark an artifact as failed."""
    case = await CaseRepository(db_session).create("Fail Art Case")
    run = await RunRepository(db_session).create(case.id)
    step = await StepRunRepository(db_session).create(run.id, "test", "step_b")

    repo = ArtifactRepository(db_session)
    art = await repo.create(
        step_run_id=step.id,
        artifact_type="cnv_seg",
        fmt="seg",
        path="/tmp/cnv.seg",
    )
    updated = await repo.mark_failed(art.id)
    assert updated.status == ArtifactStatus.FAILED


@pytest.mark.asyncio
async def test_file_checksum():
    """Verify checksum utility produces correct SHA-256."""
    content = b"test artifact content for checksum"
    expected = bytes_checksum(content)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(content)
        f.flush()
        actual = file_checksum(Path(f.name))

    assert actual == expected
    assert len(actual) == 64  # SHA-256 hex length


@pytest.mark.asyncio
async def test_artifact_list_by_case(db_session: AsyncSession):
    """List all artifacts for a case across multiple runs and steps."""
    case = await CaseRepository(db_session).create("Multi Art Case")
    run = await RunRepository(db_session).create(case.id)
    step1 = await StepRunRepository(db_session).create(run.id, "mod_a", "s1")
    step2 = await StepRunRepository(db_session).create(run.id, "mod_b", "s2")

    repo = ArtifactRepository(db_session)
    await repo.create(step_run_id=step1.id, artifact_type="type_a", fmt="json", path="/a.json")
    await repo.create(step_run_id=step2.id, artifact_type="type_b", fmt="tsv", path="/b.tsv")

    arts = await repo.list_by_case(case.id)
    assert len(arts) == 2
    types = {a.artifact_type for a in arts}
    assert types == {"type_a", "type_b"}


@pytest.mark.asyncio
async def test_artifact_download_endpoint(client: AsyncClient):
    """Download endpoint returns 404 for non-existent artifact."""
    response = await client.get("/artifacts/999/download")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_artifact_get_endpoint(client: AsyncClient):
    """GET endpoint returns 404 for non-existent artifact."""
    response = await client.get("/artifacts/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_artifact_download_path_containment(client: AsyncClient, db_session: AsyncSession):
    """Download rejects artifacts whose path is outside the data root."""
    case = await CaseRepository(db_session).create("Traversal Case")
    run = await RunRepository(db_session).create(case.id)
    step = await StepRunRepository(db_session).create(run.id, "test", "evil")

    repo = ArtifactRepository(db_session)
    # Register an artifact pointing outside data root
    art = await repo.create(
        step_run_id=step.id,
        artifact_type="evil",
        fmt="txt",
        path="/etc/passwd",
    )

    response = await client.get(f"/artifacts/{art.id}/download")
    assert response.status_code == 403
    assert "outside data root" in response.json()["detail"]


@pytest.mark.asyncio
async def test_artifact_download_valid_file(client: AsyncClient, db_session: AsyncSession):
    """Download returns the file contents for a valid artifact under data root."""
    # Create a temp file inside data root
    data_root = Path("./data").resolve()
    data_root.mkdir(parents=True, exist_ok=True)

    test_content = b"test artifact payload"
    test_file = data_root / "test_download.json"
    test_file.write_bytes(test_content)

    try:
        case = await CaseRepository(db_session).create("Download Case")
        run = await RunRepository(db_session).create(case.id)
        step = await StepRunRepository(db_session).create(run.id, "test", "dl")

        repo = ArtifactRepository(db_session)
        art = await repo.create(
            step_run_id=step.id,
            artifact_type="test_output",
            fmt="json",
            path=str(test_file),
        )

        response = await client.get(f"/artifacts/{art.id}/download")
        assert response.status_code == 200
        assert response.content == test_content
    finally:
        test_file.unlink(missing_ok=True)
