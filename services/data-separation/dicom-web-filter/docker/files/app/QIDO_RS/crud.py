from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    DicomData,
    DataProjects,
)
from sqlalchemy import select


async def get_all_studies_mapped_to_project(session: AsyncSession, project_id: int):
    stmt = (
        select(DicomData.study_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id == project_id)
    )
    result = await session.execute(stmt)
    studies = result.scalars().all()
    return studies


async def get_all_series_mapped_to_project(session: AsyncSession, project_id: int):
    stmt = (
        select(DicomData.series_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id == project_id)
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return series
