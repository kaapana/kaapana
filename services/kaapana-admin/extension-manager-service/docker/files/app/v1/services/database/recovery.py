import asyncio

from v1.services.database import crud, database
from v1.services.logger import get_logger

logger = get_logger(__name__)


async def main() -> None:
    async with database.async_session() as db:
        for extension_id in await crud.fail_interrupted_updates(db):
            logger.warning(
                "The update of extension %s was interrupted by a restart and is marked as failed", extension_id
            )


if __name__ == "__main__":
    asyncio.run(main())
