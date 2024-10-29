import traceback
from typing import List

from app.logger import get_logger
from app.models import Endpoint
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__file__)


async def add_endpoint(endpoint: str, session: AsyncSession) -> Endpoint:
    try:
        new_data = Endpoint(endpoint=endpoint)
        session.add(new_data)
        await session.commit()
        await session.refresh(new_data)
        return True

    except IntegrityError:
        await session.rollback()  # Roll back the session if there was an error
        logger.warning(f"Endpoint already exists in db: {endpoint}")
        return True

    except Exception as e:
        logger.error(f"Couldn't create endpoint. {endpoint}")
        logger.error(e)
        logger.error(traceback.format_exc())
        return False


async def remove_endpoint(endpoint: str, session: AsyncSession) -> bool:
    stmt = select(Endpoint).where(Endpoint.endpoint == endpoint)
    result = await session.execute(stmt)
    endpoint_to_delete = result.scalar()

    if endpoint_to_delete:
        await session.delete(endpoint_to_delete)
        await session.commit()


async def get_endpoints(session: AsyncSession) -> List[Endpoint]:
    stmt = select(Endpoint)
    result = await session.execute(stmt)
    return result.scalars().all()  # Return all Endpoint objects
