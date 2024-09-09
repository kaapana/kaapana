from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DataProjects, DicomData


async def get_series_instance_uids_of_study_which_are_mapped_to_project(
    session: AsyncSession, project_id: int, study_instance_uid: str
) -> List[str]:
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


async def get_all_series_of_study(
    session: AsyncSession, study_instance_uid: str
) -> List[str]:
    stmt = select(DicomData.series_instance_uid).where(
        DicomData.study_instance_uid == study_instance_uid
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return series


async def check_if_series_in_given_study_is_mapped_to_project(
    session: AsyncSession,
    project_id: int,
    study_instance_uid: str,
    series_instance_uid: str,
) -> bool:
    stmt = (
        select(DicomData.series_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id == project_id)
        .where(DicomData.study_instance_uid == study_instance_uid)
        .where(DicomData.series_instance_uid == series_instance_uid)
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return bool(series)  # If the series is found, return True, else False
