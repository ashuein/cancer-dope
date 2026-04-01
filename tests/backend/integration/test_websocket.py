"""Integration tests for the /runs/{run_id}/events WebSocket endpoint."""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.repositories import CaseRepository, RunEventRepository, RunRepository
from backend.main import app


def _make_sync_client(db_session: AsyncSession) -> TestClient:
    """Create a Starlette TestClient with overridden DB dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.mark.asyncio
async def test_ws_nonexistent_run_sends_error_and_closes(db_session: AsyncSession):
    """Connecting to a non-existent run should send an error JSON then close."""
    client = _make_sync_client(db_session)
    try:
        with client.websocket_connect("/runs/99999/events") as ws:
            data = ws.receive_json()
            assert data["error"] == "Run not found"
            assert data["run_id"] == 99999

            # The server should close the connection after the error message.
            # Starlette TestClient raises WebSocketDisconnect on close.
            with pytest.raises(WebSocketDisconnect):
                ws.receive_json()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ws_streams_existing_events(db_session: AsyncSession):
    """Events inserted before connection should be streamed with correct fields and order."""
    case = await CaseRepository(db_session).create("WS Case")
    run = await RunRepository(db_session).create(case.id)
    event_repo = RunEventRepository(db_session)

    # Insert events before connecting
    await event_repo.insert(run.id, "run_started")
    await event_repo.insert(run.id, "step_started", module="m", step_name="s1")
    await event_repo.insert(run.id, "step_completed", module="m", step_name="s1")

    client = _make_sync_client(db_session)
    try:
        with client.websocket_connect(f"/runs/{run.id}/events") as ws:
            e1 = ws.receive_json()
            assert e1["event_type"] == "run_started"
            assert e1["run_id"] == run.id
            assert "id" in e1
            assert "timestamp" in e1

            e2 = ws.receive_json()
            assert e2["event_type"] == "step_started"
            assert e2["module"] == "m"
            assert e2["step_name"] == "s1"

            e3 = ws.receive_json()
            assert e3["event_type"] == "step_completed"

            # IDs should be ascending (cursor correctness)
            assert e1["id"] < e2["id"] < e3["id"]
    finally:
        app.dependency_overrides.clear()
