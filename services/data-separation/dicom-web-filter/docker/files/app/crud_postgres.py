from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app import models
from app import schemas
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


async def get_data_project_mappings(
    session: AsyncSession,
    project_ids: List[UUID] = None,
    series_instance_uids: List[str] = None,
    study_instance_uids: List[str] = None,
) -> List[models.DataProjectMappings]:
    """
    Return all DataProjectMappings for a given project.
    """
    stmt = select(models.DataProjectMappings)
    if project_ids:
        stmt = stmt.where(models.DataProjectMappings.project_id.in_(project_ids))
    if series_instance_uids:
        stmt = stmt.where(
            models.DataProjectMappings.series_instance_uid.in_(series_instance_uids)
        )
    if study_instance_uids:
        stmt = stmt.where(
            models.DataProjectMappings.study_instance_uid.in_(study_instance_uids)
        )
    result = await session.execute(stmt)
    return result.scalars().all()


async def put_data_project_mappings(
    session: AsyncSession,
    data_project_mappings: List[schemas.DataProjectMappings],
) -> List[models.DataProjectMappings]:
    """
    Create or update a DataProjectMappings entry.
    """
    new_mappings = []
    for mapping in data_project_mappings:
        existing_mapping = await get_data_project_mappings(
            session,
            series_instance_uids=[mapping.series_instance_uid],
            project_ids=[mapping.project_id],
            study_instance_uids=[mapping.study_instance_uid],
        )

        if existing_mapping:
            logger.warning(f"Mapping {mapping} already exists.")
            continue

        new_mappings.append(
            models.DataProjectMappings(
                series_instance_uid=mapping.series_instance_uid,
                project_id=mapping.project_id,
                study_instance_uid=mapping.study_instance_uid,
            )
        )

    session.add_all(new_mappings)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Some {data_project_mappings=} already exist in the database.")

    return new_mappings


async def delete_data_project_mappings(
    session: AsyncSession,
    data_project_mappings: schemas.DataProjectMappings,
):
    """
    Delete a DataProjectMappings entry.
    """
    for mapping in data_project_mappings:
        existing_mapping = await get_data_project_mappings(
            session,
            series_instance_uids=[mapping.series_instance_uid],
            project_ids=[mapping.project_id],
        )

        if not existing_mapping:
            raise NameError(f"{mapping=} not found in the database. Cannot delete.")

        await session.delete(existing_mapping[0])

    await session.commit()
    return None
