import logging
from typing import List

from app.database import get_session
from app.keycloak_helper import KeycloakHelper, get_keycloak_helper
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


@router.get("/rights", response_model=List[schemas.Right], tags=["Projects"])
async def get_rights(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_rights(session, name=name)


@router.get("/roles", response_model=List[schemas.Role], tags=["Projects"])
async def get_roles(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_roles(session, name=name)


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
    project_name: str,
    session: AsyncSession = Depends(get_session),
    kc_client: KeycloakHelper = Depends(get_keycloak_helper),
):
    project: schemas.Project = await get_project_by_name(project_name, session)

    project_users = await crud.get_project_users_roles_mapping(session, project.id)

    keycloak_users: List[KeycloakUser] = []
    for user in project_users:
        keycloak_user_json = kc_client.get_user_by_id(user.keycloak_id)
        user = KeycloakUser(**keycloak_user_json)
        keycloak_users.append(user)

    return keycloak_users


async def get_keycloak_user(keycloak_id: str):
    kc_client = KeycloakHelper()
    keycloak_user_json = kc_client.get_user_by_id(keycloak_id)
    if not keycloak_user_json:
        raise HTTPException(status_code=404, detail="User not found")
    user = KeycloakUser(**keycloak_user_json)
    return user


@router.get(
    "/{project_name}/users/{user_id}/roles",
    response_model=schemas.Role,
    tags=["Projects"],
)
async def get_project_user_role(
    project_name: str, user_id: str, session: AsyncSession = Depends(get_session)
):
    project: schemas.Project = await get_project_by_name(project_name, session)
    user: KeycloakUser = await get_keycloak_user(user_id)

    return await crud.get_user_role_in_project(
        session, keycloak_id=user.id, project_id=project.id
    )


@router.get(
    "/{project_name}/users/{user_id}/rights",
    response_model=List[schemas.Right],
    tags=["Projects"],
)
async def get_project_user_rights(
    project_name: str, user_id: str, session: AsyncSession = Depends(get_session)
):
    project: schemas.Project = await get_project_by_name(project_name, session)
    user: KeycloakUser = await get_keycloak_user(user_id)

    result = await crud.get_user_rights_in_project(
        session, keycloak_id=user.id, project_id=project.id
    )
    if len(result) == 0:
        raise HTTPException(status_code=204, detail="No Rights Found for the User")

    return result


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

    if len(db_project) == 0 or len(db_role) == 0:
        raise HTTPException(status_code=404, detail="Project or User Role not found")

    current_user_mapping = await crud.get_users_projects_roles_mapping(
        session, db_project[0].id, user_id
    )

    if current_user_mapping:
        raise HTTPException(
            status_code=409,
            detail="Mapping already exists. Try updating if you want to update the role for the User.",
        )
    else:
        return await crud.create_users_projects_roles_mapping(
            session, db_project[0].id, db_role[0].id, user_id
        )


@router.put("/{project_name}/role/{role_name}/user/{user_id}", tags=["Projects"])
async def update_user_project_role_mapping(
    project_name: str,
    role_name: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Update a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_name)
    db_role = await crud.get_roles(session, role_name)

    if len(db_project) == 0 or len(db_role) == 0:
        raise HTTPException(status_code=404, detail="Project or User Role not found")

    current_user_mapping = await crud.get_users_projects_roles_mapping(
        session, db_project[0].id, user_id
    )

    if current_user_mapping:
        return await crud.update_users_projects_roles_mapping(
            session,
            db_project[0].id,
            user_id,
            db_role[0].id,
        )
    else:
        raise HTTPException(status_code=404, detail="Mapping not found")


@router.delete("/{project_name}/role/{role_name}/user/{user_id}", tags=["Projects"])
async def delete_user_project_role_mapping(
    project_name: str,
    role_name: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_name)
    db_role = await crud.get_roles(session, role_name)

    if len(db_project) == 0 or len(db_role) == 0:
        raise HTTPException(status_code=404, detail="Project or User Role not found")

    current_user_mapping = await crud.get_users_projects_roles_mapping(
        session, db_project[0].id, user_id
    )

    if current_user_mapping:
        return await crud.delete_users_projects_roles_mapping(
            session, db_project[0].id, db_role[0].id, user_id
        )
    else:
        raise HTTPException(status_code=404, detail="Mapping not found")
