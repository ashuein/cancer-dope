"""Worker process entrypoint for processing pipeline steps.

Each worker polls for pending StepRun records matching its queue,
executes them, and updates status + artifacts in the database.

Usage:
    python -m backend.queue.worker --queue core
    python -m backend.queue.worker --queue pvactools
    python -m backend.queue.worker --queue r
"""

import argparse
import asyncio
import logging
import signal
import sys

from backend.config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


VALID_QUEUES = {"core", "pvactools", "rnaseq", "scrna", "r", "cnv", "imaging"}


class Worker:
    """Simple polling worker that processes steps from a named queue."""

    def __init__(self, queue_name: str, poll_interval: float = 5.0):
        self.queue_name = queue_name
        self.poll_interval = poll_interval
        self._running = True

    def stop(self) -> None:
        logger.info("Shutdown signal received for queue=%s", self.queue_name)
        self._running = False

    async def run(self) -> None:
        logger.info(
            "Worker started: queue=%s, poll_interval=%.1fs",
            self.queue_name,
            self.poll_interval,
        )
        while self._running:
            try:
                claimed = await self._poll_and_claim()
                if claimed:
                    await self._execute(claimed)
                else:
                    await asyncio.sleep(self.poll_interval)
            except Exception:
                logger.exception("Worker loop error on queue=%s", self.queue_name)
                await asyncio.sleep(self.poll_interval)

        logger.info("Worker stopped: queue=%s", self.queue_name)

    async def _poll_and_claim(self) -> dict | None:
        """Poll the database for the next pending step matching this queue.

        Returns a dict with step details if one was claimed, else None.
        This is a placeholder — the real implementation will query step_runs
        where module maps to this queue and status='pending', then atomically
        set status='running'.
        """
        # TODO: implement DB polling once the repository layer is wired
        return None

    async def _execute(self, step: dict) -> None:
        """Execute a claimed step and update its status.

        This is a placeholder — the real implementation will dispatch to
        the appropriate engine module based on step['module'] and step['step_name'].
        """
        step_id = step.get("id", "?")
        logger.info("Executing step %s on queue=%s", step_id, self.queue_name)
        # TODO: dispatch to engine modules


def main() -> None:
    parser = argparse.ArgumentParser(description="PrecisionOncology pipeline worker")
    parser.add_argument(
        "--queue",
        required=True,
        choices=sorted(VALID_QUEUES),
        help="Queue name this worker processes",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between poll cycles (default: 5)",
    )
    args = parser.parse_args()

    worker = Worker(queue_name=args.queue, poll_interval=args.poll_interval)

    loop = asyncio.new_event_loop()

    def handle_signal(sig: int, frame: object) -> None:
        worker.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        loop.run_until_complete(worker.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
