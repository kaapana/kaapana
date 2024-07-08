from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    DicomData,
    DataProjects,
)
from sqlalchemy import select
from typing import List


async def get_all_studies_mapped_to_project(session: AsyncSession, project_id: int) -> List[str]:
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


async def get_all_series_mapped_to_project(session: AsyncSession, project_id: int) -> List[str]:
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

async def get_series_instance_uids_of_study_which_are_mapped_to_project(session: AsyncSession, project_id: int, study_instance_uid: str) -> List[str]:
    stmt = (
        select(DicomData.series_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id == project_id)
        .where(DicomData.study_instance_uid == study_instance_uid)
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return series