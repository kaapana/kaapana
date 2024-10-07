import logging
from typing import List

from app.database import get_session
from app.keycloak_helper import KeycloakHelper
from app.projects import crud, kubehelm, minio, opensearch, schemas
from app.schemas import KeycloakUser
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("", response_model=schemas.Project, tags=["Projects"])  # POST /projects
async def projects(
    project: schemas.CreateProject,
    session: AsyncSession = Depends(get_session),
    opensearch_helper: opensearch.OpenSearchHelper = Depends(
        opensearch.get_opensearch_helper
    ),
    minio_helper: minio.MinioHelper = Depends(minio.get_minio_helper),
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
async def get_projects(session: AsyncSession = Depends(get_session)):
    return await crud.get_projects(session, name=None)


@router.get("/{project_name}", response_model=schemas.Project, tags=["Projects"])
async def get_project_by_name(
    project_name: str, session: AsyncSession = Depends(get_session)
):
    projects = await crud.get_projects(session, name=project_name)
    if len(projects) == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects[0]


@router.get(
    "/{project_name}/users", response_model=List[KeycloakUser], tags=["Projects"]
)
async def get_project_users(
    project_name: str, session: AsyncSession = Depends(get_session)
):
    project: schemas.Project = await get_project_by_name(project_name, session)

    project_users = await crud.get_project_users_roles(session, project.id)

    kc_client = KeycloakHelper()
    keycloak_users: List[KeycloakUser] = []
    for user in project_users:
        keycloak_user_json = kc_client.get_user_by_id(user.keycloak_id)
        user = KeycloakUser(**keycloak_user_json)
        keycloak_users.append(user)

    return keycloak_users


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

    try:
        return await crud.create_users_projects_roles_mapping(
            session, db_project[0].id, db_role[0].id, user_id
        )
    except IntegrityError as e:
        return Response(f"Mapping already exists", status_code=200)
