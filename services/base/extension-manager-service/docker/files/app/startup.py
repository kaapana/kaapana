"""Create the tables and register the default extension repository before the API workers start."""

import asyncio
import os

from v1.services.database import database
from v1.services.default_repository import ensure_default_repository
from v1.services.logger import get_logger

logger = get_logger(__name__)


async def main() -> None:
    try:
        await database.init_db()
        try:
            async with database.async_session() as session:
                await ensure_default_repository(
                    session,
                    url=os.getenv("DEFAULT_EXTENSION_REPOSITORY_URL", ""),
                    username=os.getenv("DEFAULT_EXTENSION_REPOSITORY_USERNAME", ""),
                    password=os.getenv("DEFAULT_EXTENSION_REPOSITORY_PASSWORD", ""),
                )
        except Exception:
            # The extension manager must stay usable without the default repository.
            logger.exception("The default extension repository could not be registered.")
    finally:
        await database.async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
