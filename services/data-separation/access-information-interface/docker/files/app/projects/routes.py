from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List
from . import schemas
from . import crud
from . import opensearch
from . import minio
from . import kubehelm

from ..database import get_session
import logging

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("", response_model=schemas.Project, tags=["Projects"])  # POST /projects
async def projects(
    project: schemas.CreateProject,
    session: AsyncSession = Depends(get_session),
    opensearch_helper=Depends(opensearch.get_opensearch_helper),
    minio_helper=Depends(minio.get_minio_helper),
):
    try:
        created_project = await crud.create_project(session, project)
    except IntegrityError as e:
        logger.warning(f"{project=} already exists!")
        await session.rollback()
        db_project = await crud.get_projects(session, project.name)
        created_project = db_project[0]
    opensearch_helper.setup_new_project(created_project)
    minio_helper.setup_new_project(created_project)
    kubehelm.install_project_helm_chart(created_project)
    return created_project


@router.get("", response_model=List[schemas.Project], tags=["Projects"])
async def get_projects(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_projects(session, name=name)


@router.get("/rights", response_model=List[schemas.Right], tags=["Projects"])
async def get_rights(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_rights(session, name=name)


@router.get("/roles", response_model=List[schemas.Role], tags=["Projects"])
async def get_roles(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_roles(session, name=name)


@router.post("/{project_name}/role/{role_name}/user/{user_id}", tags=["Projects"])
async def post_user_project_role_mapping(
    project_name: str,
    role_name: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Create a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_name)
    db_role = await crud.get_roles(session, role_name)

    return await crud.create_users_projects_roles_mapping(
        session, db_project[0].id, db_role[0].id, user_id
    )


@router.post("/{project_name}/data", response_model=schemas.Data, tags=["Projects"])
async def create_data(
    project_name: str,
    data: schemas.CreateData,
    session: AsyncSession = Depends(get_session),
):
    try:
        stored_data = await crud.create_data(session, data)
    except IntegrityError as e:
        logger.warning(f"{data=} already exists")
        await session.rollback()
        stored_data = await crud.get_data(
            session=session, series_instance_uid=data.series_instance_uid
        )
        stored_data = stored_data[0]
    projects = await crud.get_projects(session, name=project_name)
    try:
        await crud.create_data_projects_mapping(
            session, project_id=projects[0].id, data_id=stored_data.id
        )
    except IntegrityError as e:
        logger.warning(f"DataProjects mapping already exists")
        return Response("Data mapping already exists", 200)
    return stored_data
