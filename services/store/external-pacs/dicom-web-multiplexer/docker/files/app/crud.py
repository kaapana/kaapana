import traceback
from typing import List

from app.logger import get_logger
from app.models import DataSource
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__file__)


async def add_datasource(datasource: DataSource, session: AsyncSession) -> DataSource | None:
    try:
        session.add(datasource)
        await session.commit()
        return await session.refresh(datasource)

    except IntegrityError:
        await session.rollback()
        logger.warning(f"Datasource already exists in db: {datasource}")

    except Exception as e:
        logger.error(
            f"Couldn't create datasource: {datasource}"
        )
        logger.error(e)
        logger.error(traceback.format_exc())
        


async def remove_datasource(datasource: DataSource, session: AsyncSession):
    stmt = select(DataSource).where(
        DataSource.dcmweb_endpoint == datasource.dcmweb_endpoint,
        DataSource.opensearch_index == datasource.opensearch_index,
    )
    result = await session.execute(stmt)
    endpoint_to_delete = result.scalar()

    if endpoint_to_delete:
        await session.delete(endpoint_to_delete)
        await session.commit()


async def get_all_datasources(
    opensearch_index: str, session: AsyncSession
) -> List[DataSource]:
    stmt = select(DataSource).where(DataSource.opensearch_index == opensearch_index)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_datasource(
    datasource: DataSource, session: AsyncSession
) -> List[DataSource]:
    stmt = select(DataSource).where(
        DataSource.dcmweb_endpoint == datasource.dcmweb_endpoint,
        DataSource.opensearch_index == datasource.opensearch_index,
    )
    result = await session.execute(stmt)
    return result.scalars().all()
