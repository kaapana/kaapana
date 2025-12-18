import asyncio
import logging
from app.api.v1.services import workflow_run_service
from app.dependencies import get_async_db

logger = logging.getLogger(__name__)


async def run_sync(interval_seconds: int = 60):
    """
    Infinite loop that triggers the sync service every interval_seconds seconds.
    """
    logger.info("Syncing started.")
    while True:
        try:
            # manually manage the DB session
            async for db in get_async_db():
                await workflow_run_service.sync_active_runs(db)
                # we break after one yield because get_async_db yields a session and closes it after the context manager exits
                break
        except Exception as e:
            logger.error(f"Sync encountered an error: {e}")

        await asyncio.sleep(interval_seconds)
