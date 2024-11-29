from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DataProjects, DicomData


async def get_all_studies_mapped_to_projects(
    session: AsyncSession, project_ids: List[int]
) -> List[str]:
    stmt = (
        select(DicomData.study_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id.in_(project_ids))
    )
    result = await session.execute(stmt)
    studies = result.scalars().all()
    return studies


async def get_all_series_mapped_to_projects(
    session: AsyncSession, project_ids: List[int]
) -> List[str]:
    stmt = (
        select(DicomData.series_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id.in_(project_ids))
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return series


async def get_series_instance_uids_of_study_which_are_mapped_to_projects(
    session: AsyncSession, project_ids: List[int], study_instance_uid: str
) -> List[str]:
    stmt = (
        select(DicomData.series_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id.in_(project_ids))
        .where(DicomData.study_instance_uid == study_instance_uid)
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return series


async def check_if_series_in_given_study_is_mapped_to_projects(
    session: AsyncSession,
    project_ids: List[int],
    study_instance_uid: str,
    series_instance_uid: str,
) -> bool:
    stmt = (
        select(DicomData.series_instance_uid)
        .join(
            DataProjects,
            DataProjects.series_instance_uid == DicomData.series_instance_uid,
        )
        .where(DataProjects.project_id.in_(project_ids))
        .where(DicomData.study_instance_uid == study_instance_uid)
        .where(DicomData.series_instance_uid == series_instance_uid)
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return len(series) > 0


async def add_dicom_data(
    session: AsyncSession,
    series_instance_uid: str,
    study_instance_uid: str,
    description: str,
) -> DicomData:
    new_data = DicomData(
        series_instance_uid=series_instance_uid,
        study_instance_uid=study_instance_uid,
        description=description,
    )
    session.add(new_data)
    await session.commit()
    return new_data


async def get_data_of_project(session: AsyncSession, project_id: int):
    """
    Return all data that belongs to a project.
    """
    stmt = select(DicomData)
    stmt = stmt.join(DicomData.data_projects)
    stmt = stmt.where(DataProjects.project_id == project_id)
    result = await session.execute(stmt)
    data = result.scalars().all()
    return data


async def get_projects_of_data(session: AsyncSession, series_instance_uid: str):
    """
    Return all projects where data belongs to.
    """
    stmt = select(DataProjects.project_id)
    stmt = stmt.where(DataProjects.series_instance_uid == series_instance_uid)
    result = await session.execute(stmt)
    project_ids = result.scalars().all()
    return project_ids


async def add_data_project_mapping(
    session: AsyncSession, series_instance_uid: str, project_id: int
) -> DataProjects:
    new_mapping = DataProjects(
        series_instance_uid=series_instance_uid, project_id=project_id
    )
    session.add(new_mapping)
    await session.commit()
    return new_mapping


async def get_all_series_of_study(
    session: AsyncSession, study_instance_uid: str
) -> List[str]:
    stmt = select(DicomData.series_instance_uid).where(
        DicomData.study_instance_uid == study_instance_uid
    )
    result = await session.execute(stmt)
    series = result.scalars().all()
    return series


async def get_data_project_mapping(session, series_instance_uid: str, project_id: int):
    stmt = select(DataProjects)
    stmt = stmt = stmt.where(
        DataProjects.series_instance_uid == series_instance_uid,
        DataProjects.project_id == project_id,
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def remove_data_project_mapping(
    session: AsyncSession, series_instance_uid: str, project_id: int
):
    """
    Delete a DataProject mapping.
    """
    remove_mapping = await get_data_project_mapping(
        session, series_instance_uid=series_instance_uid, project_id=project_id
    )
    session.delete(remove_mapping[0])
    await session.commit()
    return None
