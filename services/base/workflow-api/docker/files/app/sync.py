import asyncio
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.v1.services import workflow_run_service
from app.config import settings
from app.dependencies import get_async_db

logger = logging.getLogger(__name__)

# The value is arbitrary. The service has its own database, so no other application uses this key.
SYNC_LOCK_KEY = 8_734_201

# The advisory lock belongs to the database session. Without a pool, closing the connection ends
# the session and releases the lock. A pooled connection would keep the lock after its return.
# Autocommit keeps the long-lived connection from holding an open transaction.
_lock_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    poolclass=NullPool,
    isolation_level="AUTOCOMMIT",
)


async def _close_lock_connection(conn: AsyncConnection) -> None:
    try:
        await conn.close()
    except Exception as e:
        logger.debug(f"Closing the sync lock connection failed: {e}")


async def _sync_active_runs() -> None:
    try:
        # manually manage the DB session
        async for db in get_async_db():
            await workflow_run_service.sync_active_runs(db)
            # we break after one yield because get_async_db yields a session and closes it after the context manager exits
            break
    except Exception as e:
        logger.error(f"Sync encountered an error: {e}")


async def run_sync(interval_seconds: int = 60):
    """
    Infinite loop that triggers the sync service every interval_seconds seconds.

    Every worker process runs this loop, but only the worker that holds the sync lock runs the sync.
    The other workers try to take the lock in every interval, so that one of them takes over
    when the current holder stops.
    """
    pid = os.getpid()
    lock_conn: AsyncConnection | None = None
    holds_lock = False
    try:
        while True:
            try:
                if lock_conn is None:
                    lock_conn = await _lock_engine.connect()
                if holds_lock:
                    await lock_conn.execute(text("SELECT 1"))
                else:
                    result = await lock_conn.execute(
                        text("SELECT pg_try_advisory_lock(:key)"),
                        {"key": SYNC_LOCK_KEY},
                    )
                    holds_lock = bool(result.scalar())
                    if holds_lock:
                        logger.info(f"Worker {pid} took the sync lock and now runs the periodic sync.")
                    else:
                        logger.debug(f"Worker {pid} skips the periodic sync because another worker holds the lock.")
            except Exception as e:
                # A failed call can mean that the session ended and released the lock.
                # Only a new session can safely take the lock again.
                logger.error(f"Sync lock connection failed: {e}")
                if holds_lock:
                    logger.info(f"Worker {pid} lost the sync lock and stops running the periodic sync.")
                if lock_conn is not None:
                    await _close_lock_connection(lock_conn)
                lock_conn = None
                holds_lock = False

            if holds_lock:
                await _sync_active_runs()
            await asyncio.sleep(interval_seconds)
    finally:
        if lock_conn is not None:
            await _close_lock_connection(lock_conn)
