from typing import List

from app.models import Endpoint
from sqlalchemy import select
from sqlalchemy.ext import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def add_endpoint(session: AsyncSession, endpoint: str) -> Endpoint:
    try:
        new_data = Endpoint(endpoint=endpoint)
        session.add(new_data)
        await session.commit()
        await session.refresh(new_data)
        return new_data

    except IntegrityError:
        await session.rollback()  # Roll back the session if there was an error
        raise ValueError(f"Endpoint '{endpoint}' already exists.")


async def remove_endpoint(session: AsyncSession, endpoint: str) -> bool:
    stmt = select(Endpoint).where(Endpoint.endpoint == endpoint)
    result = await session.execute(stmt)
    endpoint_to_delete = result.scalar()

    if endpoint_to_delete:
        await session.delete(endpoint_to_delete)
        await session.commit()
        return True

    return False  # Return False if the endpoint was not found


async def get_endpoints(session: AsyncSession) -> List[Endpoint]:
    stmt = select(Endpoint)
    result = await session.execute(stmt)
    return result.scalars().all()  # Return all Endpoint objects
