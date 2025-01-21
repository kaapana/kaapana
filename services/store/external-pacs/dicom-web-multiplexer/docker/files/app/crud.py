from typing import List

from app.logger import get_logger
from app.models import DataSourceDB
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__file__)


async def add_datasource(
    datasource: DataSourceDB, session: AsyncSession
) -> DataSourceDB | None:
    try:
        session.add(datasource)
        await session.commit()

    except IntegrityError:
        await session.rollback()


async def remove_datasource(datasource: DataSourceDB, session: AsyncSession):
    stmt = select(DataSourceDB).where(
        DataSourceDB.dcmweb_endpoint == datasource.dcmweb_endpoint,
        DataSourceDB.project_index == datasource.project_index,
    )
    result = await session.execute(stmt)
    endpoint_to_delete = result.scalar()

    if endpoint_to_delete:
        await session.delete(endpoint_to_delete)
        await session.commit()


async def get_all_datasources(
    project_index: str, session: AsyncSession
) -> List[DataSourceDB]:
    stmt = select(DataSourceDB).where(DataSourceDB.project_index == project_index)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_datasource(
    datasource: DataSourceDB, session: AsyncSession
) -> List[DataSourceDB]:
    stmt = select(DataSourceDB).where(
        DataSourceDB.dcmweb_endpoint == datasource.dcmweb_endpoint,
        DataSourceDB.project_index == datasource.project_index,
    )
    result = await session.execute(stmt)
    return result.scalars().all()
