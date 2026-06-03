import json
import logging
import os
from typing import List, Optional
from uuid import UUID

from app.database import get_session
from app.keycloak_helper import KeycloakHelper, get_keycloak_helper
from app.projects import crud, dicom_data, kubehelm, minio, opensearch, schemas
from app.schemas import KeycloakUser
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from requests.exceptions import HTTPError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

CONFIG_DIR = os.environ.get("CONFIG_DIR", "/app/config")

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

    created_project = await crud.get_projects(session, project_name=project.name)
    created_project = created_project[0]

    await opensearch_helper.setup_new_project(project=created_project, session=session)
    await minio_helper.setup_new_project(project=created_project, session=session)
    kubehelm.install_project_helm_chart(created_project)

    with open(f"{CONFIG_DIR}/default_software.json") as f:
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

    return schemas.Project(**created_project.__dict__)


@router.get("", response_model=List[schemas.Project], tags=["Projects"])
async def get_projects(session: AsyncSession = Depends(get_session)):
    return await crud.get_projects(session)


@router.get("/admin", response_model=schemas.Project, tags=["Projects"])
async def get_admin_project(session: AsyncSession = Depends(get_session)):
    project = await crud.get_admin_project(session)
    if not project:
        raise HTTPException(status_code=404, detail="Admin project not yet found")
    return project


@router.get("/rights", response_model=List[schemas.Right], tags=["Projects"])
async def get_rights(
    session: AsyncSession = Depends(get_session), name: Optional[str] = None
):
    return await crud.get_rights(session, name=name)


@router.post("/rights", response_model=schemas.Right, tags=["Projects"])
async def create_right(
    right: schemas.CreateRight,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await crud.create_rights(session, right)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"Right '{right.name}' already exists.")


@router.put("/rights/{right_id}", response_model=schemas.Right, tags=["Projects"])
async def update_right(
    right_id: int,
    right: schemas.CreateRight,
    session: AsyncSession = Depends(get_session),
):
    updated = await crud.update_right(session, right_id, right)
    if not updated:
        raise HTTPException(status_code=404, detail="Right not found")
    return updated


@router.delete("/rights/{right_id}", status_code=204, tags=["Projects"])
async def delete_right(
    right_id: int,
    session: AsyncSession = Depends(get_session),
):
    await crud.delete_right(session, right_id)
    return Response(status_code=204)


@router.post("/rights/reset", tags=["Projects"])
async def reset_role_rights(
    session: AsyncSession = Depends(get_session),
):
    """Reset all rights and role-rights mappings to the defaults from the configmap."""
    rights_path = f"{CONFIG_DIR}/initial_rights.json"
    mappings_path = f"{CONFIG_DIR}/initial_roles_rights_mapping.json"
    try:
        with open(rights_path) as f:
            default_rights = json.load(f)
        with open(mappings_path) as f:
            mappings = json.load(f)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Config file not found: {e}")

    all_db_rights = await crud.get_rights(session)
    deleted_rights = len(all_db_rights)
    for db_right in all_db_rights:
        await crud.delete_right(session, db_right.id)

    for right_data in default_rights:
        await crud.create_rights(session, schemas.CreateRight(**right_data))

    reset_count = 0
    for mapping in mappings:
        role_name = mapping["role"]
        right_names = mapping["rights"]

        roles = await crud.get_roles(session, name=role_name)
        if not roles:
            logger.warning(f"Role '{role_name}' not found, skipping.")
            continue
        role = roles[0]

        await crud.delete_all_rights_for_role(session, role.id)

        for right_name in right_names:
            rights = await crud.get_rights(session, name=right_name)
            if not rights:
                logger.warning(f"Right '{right_name}' not found after recreation, skipping.")
                continue
            try:
                await crud.create_roles_rights_mapping(session, role.id, rights[0].id)
                reset_count += 1
            except Exception as e:
                logger.warning(f"Could not assign '{right_name}' to '{role_name}': {e}")

    return {"reset": reset_count, "deleted_rights": deleted_rights}


@router.get("/roles", response_model=List[schemas.Role], tags=["Projects"])
async def get_roles(
    session: AsyncSession = Depends(get_session), name: Optional[str] = None
):
    return await crud.get_roles(session, name=name)



@router.get("/roles/{role_id}/rights", response_model=List[schemas.Right], tags=["Projects"])
async def get_role_rights(
    role_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await crud.get_rights_by_role_id(session, role_id)


@router.post("/roles/{role_id}/right/{right_id}", status_code=204, tags=["Projects"])
async def assign_right_to_role(
    role_id: int,
    right_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        await crud.create_roles_rights_mapping(session, role_id, right_id)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Mapping already exists.")
    return Response(status_code=204)


@router.delete("/roles/{role_id}/right/{right_id}", status_code=204, tags=["Projects"])
async def remove_right_from_role(
    role_id: int,
    right_id: int,
    session: AsyncSession = Depends(get_session),
):
    await crud.delete_roles_rights_mapping(session, role_id, right_id)
    return Response(status_code=204)


@router.get("/{project_identifier}", response_model=schemas.Project, tags=["Projects"])
async def get_project(
    project_identifier: str | UUID, session: AsyncSession = Depends(get_session)
):
    # convert to str in case type is UUID
    project_identifier = str(project_identifier)

    if project_identifier == "admin":
        projects = await crud.get_admin_project(session)

    # resolve project identifier with the order: UUID → short_id (8 chars) → name
    try:
        projects = await crud.get_projects(session, project_id=UUID(project_identifier))
    except ValueError:
        if len(project_identifier) == 8:
            projects = await crud.get_projects(
                session, project_short_id=project_identifier
            )
        else:
            projects = []

        # TODO: remove the project_name altogether, projects should only be identifiable via their UUID or short_id.
        # The project_name is not unique
        if not projects:
            projects = await crud.get_projects(session, project_name=project_identifier)

    if len(projects) == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects[0]


@router.put("/{project_id}", response_model=schemas.Project, tags=["Projects"])
async def update_project(
    project_id: UUID,
    project_update: schemas.UpdateProject,
    session: AsyncSession = Depends(get_session),
    opensearch_helper: opensearch.OpenSearchHelper = Depends(
        opensearch.get_opensearch_helper
    ),
):
    """
    Edit a project's name, description or external_id.

    * The OpenSearch alias is updated to `project-<new_name>`.
    * The Kubernetes namespace label `kaapana.ai/project-name` is patched to the new name
    """
    existing = await crud.get_projects(session, project_id=project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    admin_project = await crud.get_admin_project(session)
    if admin_project and admin_project.id == project_id:
        raise HTTPException(status_code=403, detail="Cannot edit the admin project")

    if existing[0].is_archived:
        raise HTTPException(status_code=403, detail="Cannot modify an archived project")

    old_project = existing[0]
    old_name = old_project.name

    updated_project = await crud.update_project(session, project_id, project_update)

    # Propagate a name change to aliases / labels
    new_name = updated_project.name
    if project_update.name is not None and new_name != old_name:
        await opensearch_helper.update_project_alias(
            project=updated_project, old_name=old_name
        )
        # TODO: Patch the k8s namespace label via and Helm label (if exists) via a Helm upgrade

    return schemas.Project(**updated_project.__dict__)


@router.post("/{project_id}/archive", response_model=schemas.Project, tags=["Projects"])
async def archive_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Set a project to archived (read-only). Data is preserved."""
    existing = await crud.get_projects(session, project_id=project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    admin_project = await crud.get_admin_project(session)
    if admin_project and admin_project.id == project_id:
        raise HTTPException(status_code=403, detail="Cannot archive the admin project")

    return await crud.set_project_archived(session, project_id, archived=True)


@router.post(
    "/{project_id}/unarchive", response_model=schemas.Project, tags=["Projects"]
)
async def unarchive_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Restore an archived project to active state."""
    existing = await crud.get_projects(session, project_id=project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    return await crud.set_project_archived(session, project_id, archived=False)


@router.delete("/{project_id}", tags=["Projects"])
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    opensearch_helper: opensearch.OpenSearchHelper = Depends(
        opensearch.get_opensearch_helper
    ),
    minio_helper: minio.MinioHelper = Depends(minio.get_minio_helper),
):
    """
    Delete a Kaapana project: drops the S3 bucket, OpenSearch index, roles, helm chart and dicom series held only by this project (and admin).


    """
    existing = await crud.get_projects(session, project_id=project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    project = existing[0]

    admin_project = await crud.get_admin_project(session)
    if admin_project and admin_project.id == project_id:
        raise HTTPException(status_code=403, detail="Cannot delete the admin project")

    # Delete series held only by this project (and admin) from the platform.
    # Targets the DAG at admin's context since admin always holds every series.
    if admin_project is not None:
        admin_project_schema = schemas.Project.model_validate(admin_project)
        orphan_series = dicom_data.get_orphan_series(
            project_id=project_id, admin_project_id=admin_project.id
        )
        dicom_data.clear_project_mappings(project_id=project_id)
        try:
            dicom_data.trigger_delete_series_dag(
                admin_project=admin_project_schema, series_uids=orphan_series
            )
        except Exception as e:
            logger.warning(f"delete-series DAG trigger failed for {project_id}: {e}")

    await opensearch_helper.teardown_project(project=project, session=session)
    await minio_helper.teardown_project(project=project, session=session)
    kubehelm.uninstall_project_helm_chart(project)
    await crud.delete_project(session, project_id)

    return Response(status_code=204)


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
        try:
            keycloak_user_json = kc_client.get_user_by_id(user.keycloak_id)
        except HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"{user=} not found in Keycloak database.")
                continue
            else:
                raise e
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

    if db_project[0].is_archived:
        raise HTTPException(status_code=403, detail="Cannot modify an archived project")

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

    if db_project[0].is_archived:
        raise HTTPException(status_code=403, detail="Cannot modify an archived project")

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

    if db_project[0].is_archived:
        raise HTTPException(status_code=403, detail="Cannot modify an archived project")

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

    if project.is_archived:
        raise HTTPException(status_code=403, detail="Cannot modify an archived project")

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

    if project.is_archived:
        raise HTTPException(status_code=403, detail="Cannot modify an archived project")

    for software in softwares:
        await crud.delete_software_mapping(
            session, project_id=project.id, software_uuid=software.software_uuid
        )

    return Response(status_code=204)


@router.get(
    "/{project_id}/multiinstallable-whitelist",
    response_model=List[str],
    tags=["Projects"],
)
async def get_multiinstallable_whitelist(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> List[str]:
    project: schemas.Project = await get_project(str(project_id), session)
    return await crud.get_multiinstallable_whitelist_by_project_id(session, project.id)


@router.put(
    "/{project_id}/multiinstallable-whitelist",
    response_model=List[str],
    tags=["Projects"],
)
async def update_multiinstallable_whitelist(
    project_id: UUID,
    payload: schemas.UpdateMultiinstallableWhitelist,
    session: AsyncSession = Depends(get_session),
) -> List[str]:
    project: schemas.Project = await get_project(str(project_id), session)
    return await crud.update_multiinstallable_whitelist_by_project_id(
        session, project.id, payload.app_names
    )
