import json
import logging
from typing import List, Optional
from uuid import UUID

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
    """
    Create a new Kaapana project:
    - Create a new project in the database
    - Create a project index in OpenSearch as well as the necessary roles and role-mappings
    - Create a project bucket in Minio as well as the necessary policies
    - Install the project-namespace Helm chart
    - Add default software mappings to the project.
    """
    try:
        await opensearch_helper.check_project_template_exists()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        created_project = await crud.create_project(session, project)
        if project.default:
            await crud.set_admin_project(session, project_id=created_project.id)

    except IntegrityError:
        logger.warning(f"{project=} already exists!")
        await session.rollback()
        created_project = await crud.get_projects(session, project_name=project.name)[0]
        return created_project

    response_project = schemas.Project(**created_project.__dict__)
    await opensearch_helper.setup_new_project(project=created_project, session=session)
    await minio_helper.setup_new_project(project=created_project, session=session)
    kubehelm.install_project_helm_chart(created_project)

    with open("/app/config/default_software.json") as f:
        default_software = json.load(f)

    created_project_id = created_project.id
    for mapping in default_software:
        try:
            await crud.create_software_mapping(
                session, created_project_id, mapping.get("software_uuid")
            )
        except IntegrityError as e:
            logger.warning(
                f"Software mapping {mapping.get('software_uuid')} already exists!"
            )
            await session.rollback()

    return response_project


@router.get("", response_model=List[schemas.Project], tags=["Projects"])
async def get_projects(session: AsyncSession = Depends(get_session)):
    print(crud.get_projects(session))
    return await crud.get_projects(session)


@router.get("/admin", response_model=schemas.Project, tags=["Projects"])
async def get_admin_project(session: AsyncSession = Depends(get_session)):
    project = await crud.get_admin_project(session)
    print(project)
    return project


@router.get("/rights", response_model=List[schemas.Right], tags=["Projects"])
async def get_rights(
    session: AsyncSession = Depends(get_session), name: Optional[str] = None
):
    return await crud.get_rights(session, name=name)


@router.get("/roles", response_model=List[schemas.Role], tags=["Projects"])
async def get_roles(
    session: AsyncSession = Depends(get_session), name: Optional[str] = None
):
    return await crud.get_roles(session, name=name)


@router.get("/{project_identifier}", response_model=schemas.Project, tags=["Projects"])
async def get_project(
    project_identifier: str | UUID, session: AsyncSession = Depends(get_session)
):
    if project_identifier == "admin":
        projects = await crud.get_admin_project(session)

    if isinstance(project_identifier, UUID):
        projects = await crud.get_projects(session, project_id=project_identifier)
    else:
        try:
            project_id = UUID(project_identifier)
            projects = await crud.get_projects(session, project_id=project_id)
        except ValueError:
            projects = await crud.get_projects(session, project_name=project_identifier)

    if len(projects) == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects[0]


@router.get("/{project_id}/users", response_model=List[KeycloakUser], tags=["Projects"])
async def get_project_users(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    kc_client: KeycloakHelper = Depends(get_keycloak_helper),
):
    project: schemas.Project = await get_project(str(project_id), session)

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
    "/{project_id}/users/{user_id}/roles",
    response_model=schemas.Role,
    tags=["Projects"],
)
async def get_project_user_role(
    project_id: UUID, user_id: str, session: AsyncSession = Depends(get_session)
):
    project: schemas.Project = await get_project(project_id, session)
    user: KeycloakUser = await get_keycloak_user(user_id)

    try:
        return await crud.get_user_role_in_project(
            session, keycloak_id=user.id, project_id=project.id
        )
    except Exception:
        raise HTTPException(status_code=204, detail="No Role found for the User")


@router.get(
    "/{project_id}/users/{user_id}/rights",
    response_model=List[schemas.Right],
    tags=["Projects"],
)
async def get_project_user_rights(
    project_id: UUID, user_id: str, session: AsyncSession = Depends(get_session)
):
    project: schemas.Project = await get_project(project_id, session)
    user: KeycloakUser = await get_keycloak_user(user_id)

    try:
        result = await crud.get_user_rights_in_project(
            session, keycloak_id=user.id, project_id=project.id
        )
    except Exception:
        raise HTTPException(status_code=204, detail="No Rights found for the User")

    if len(result) == 0:
        raise HTTPException(status_code=204, detail="No Rights Found for the User")

    return result


@router.post("/{project_id}/role/{role_name}/user/{user_id}", tags=["Projects"])
async def post_user_project_role_mapping(
    project_id: UUID,
    role_name: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Create a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_id)
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


@router.put("/{project_id}/user/{user_id}/rolemapping", tags=["Projects"])
async def update_user_project_role_mapping(
    project_id: UUID,
    user_id: str,
    role_name: str,
    session: AsyncSession = Depends(get_session),
):
    """Update a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_id)
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


@router.delete("/{project_id}/user/{user_id}/rolemapping", tags=["Projects"])
async def delete_user_project_role_mapping(
    project_id: UUID,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_id)

    if len(db_project) == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    current_user_mapping = await crud.get_users_projects_roles_mapping(
        session, db_project[0].id, user_id
    )

    if current_user_mapping:
        return await crud.delete_users_projects_roles_mapping(
            session, db_project[0].id, user_id
        )
    else:
        raise HTTPException(status_code=404, detail="Mapping not found")


### Software separation


@router.get(
    "/{project_id}/software-mappings",
    response_model=List[schemas.Software],
    tags=["Projects"],
)
async def get_software_mappings(
    project_id: UUID, session: AsyncSession = Depends(get_session)
) -> List[schemas.Software]:
    project: schemas.Project = await get_project(str(project_id), session)
    return await crud.get_software_mappings_by_project_id(session, project.id)


@router.post(
    "/{project_id}/software-mappings",
    response_model=List[schemas.Software],
    tags=["Projects"],
)
async def create_software_mappings(
    project_id: UUID,
    softwares: List[schemas.Software],
    session: AsyncSession = Depends(get_session),
):
    project: schemas.Project = await get_project(project_id, session)

    return [
        await crud.create_software_mapping(
            session, project_id=project.id, software_uuid=software.software_uuid
        )
        for software in softwares
    ]


@router.delete(
    "/{project_id}/software-mappings",
    tags=["Projects"],
)
async def delete_software_mappings(
    project_id: UUID,
    softwares: List[schemas.Software],
    session: AsyncSession = Depends(get_session),
):
    project: schemas.Project = await get_project(project_id, session)
    for software in softwares:
        await crud.delete_software_mapping(
            session, project_id=project.id, software_uuid=software.software_uuid
        )

    return Response(status_code=204)
