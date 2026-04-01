"""WebSocket endpoint for real-time run events.

Clients connect to /runs/{run_id}/events and receive JSON events as the
pipeline runner progresses through steps.

The event bus is DB-backed: workers INSERT into the run_events table,
and this endpoint polls for new rows. This works across container
boundaries without requiring an in-memory broker.

Idle disconnect detection: during quiet periods we race the poll sleep
against a client receive so that disconnects are noticed promptly even
when there are no events to send.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.db.database import get_session
from backend.db.repositories import RunEventRepository, RunRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

POLL_INTERVAL = 0.5  # seconds between DB polls


@router.websocket("/runs/{run_id}/events")
async def run_events(websocket: WebSocket, run_id: int):
    await websocket.accept()

    # Validate that the run exists before entering the poll loop.
    async with get_session() as db:
        run = await RunRepository(db).get(run_id)

    if run is None:
        await websocket.send_json({"error": "Run not found", "run_id": run_id})
        await websocket.close(code=4004, reason="Run not found")
        return

    last_seen_id = 0

    # A persistent task that completes when the client disconnects.
    # We race this against the poll sleep to detect idle disconnects.
    disconnect_task = asyncio.ensure_future(_wait_for_disconnect(websocket))

    try:
        while not disconnect_task.done():
            async with get_session() as db:
                repo = RunEventRepository(db)
                events = await repo.poll_after(run_id, after_id=last_seen_id)

            for event in events:
                await websocket.send_json({
                    "id": event.id,
                    "run_id": event.run_id,
                    "step_run_id": event.step_run_id,
                    "event_type": event.event_type,
                    "module": event.module,
                    "step_name": event.step_name,
                    "error_message": event.error_message,
                    "timestamp": event.created_at.isoformat() if event.created_at else None,
                })
                last_seen_id = event.id

            # Sleep, but break early if the client disconnects.
            sleep_task = asyncio.ensure_future(asyncio.sleep(POLL_INTERVAL))
            done, _ = await asyncio.wait(
                {disconnect_task, sleep_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if disconnect_task in done:
                sleep_task.cancel()
                break
    except WebSocketDisconnect:
        pass
    finally:
        if not disconnect_task.done():
            disconnect_task.cancel()


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    """Block until the client sends a message or disconnects.

    We don't expect the client to send meaningful data — this just
    lets us detect a closed connection during idle periods.
    """
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
