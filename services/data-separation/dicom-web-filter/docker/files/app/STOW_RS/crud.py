from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DataProjects, DicomData


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


async def add_data_project_mapping(
    session: AsyncSession, series_instance_uid: str, project_id: int
) -> DataProjects:
    new_mapping = DataProjects(
        series_instance_uid=series_instance_uid, project_id=project_id
    )
    session.add(new_mapping)
    await session.commit()
    return new_mapping
