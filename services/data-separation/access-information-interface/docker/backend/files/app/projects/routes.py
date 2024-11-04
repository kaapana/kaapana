import logging
import re
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


def validate_project_name(project_name: str):
    valid_bucket_name = minio.is_valid_minio_bucket_name(project_name)
    if not valid_bucket_name:
        return False, "Invalid MINIO bucket name"

    valid_opensearch_index_name = opensearch.is_valid_opensearch_index_name(
        project_name
    )
    if not valid_opensearch_index_name:
        return False, "Invalid OpenSearch Index name"

    valid_kubernetes_namespace = kubehelm.is_valid_kubernetes_namespace(project_name)
    if not valid_kubernetes_namespace:
        return False, "Invalid Kubernetes Namespace"

    # AE title can only be uppercase, project name converted to uppercase
    # for validation
    valid_ae_title = is_valid_dicom_ae_title(project_name.upper())
    if not valid_ae_title:
        return False, "Invalid AE TITLE"
    return True, ""


@router.post("", response_model=schemas.Project, tags=["Projects"])  # POST /projects
async def projects(
    project: schemas.CreateProject,
    session: AsyncSession = Depends(get_session),
    opensearch_helper: opensearch.OpenSearchHelper = Depends(
        opensearch.get_opensearch_helper
    ),
    minio_helper: minio.MinioHelper = Depends(minio.get_minio_helper),
):
    # validate the project name first
    isvalid, message = validate_project_name(project.name)
    if not isvalid:
        raise HTTPException(
            status_code=400, detail=str(f"Project Name Validation Failed: {message}")
        )

    try:
        await opensearch_helper.check_project_template_exists()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
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

    try:
        return await crud.get_user_role_in_project(
            session, keycloak_id=user.id, project_id=project.id
        )
    except Exception as e:
        raise HTTPException(status_code=204, detail="No Role found for the User")


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

    try:
        result = await crud.get_user_rights_in_project(
            session, keycloak_id=user.id, project_id=project.id
        )
    except Exception as e:
        raise HTTPException(status_code=204, detail="No Rights found for the User")

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


@router.put("/{project_name}/user/{user_id}/rolemapping", tags=["Projects"])
async def update_user_project_role_mapping(
    project_name: str,
    user_id: str,
    role_name: str,
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


@router.delete("/{project_name}/user/{user_id}/rolemapping", tags=["Projects"])
async def delete_user_project_role_mapping(
    project_name: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a UserProjectRole mapping"""
    db_project = await crud.get_projects(session, project_name)

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


def is_valid_dicom_ae_title(ae_title: str) -> bool:
    """
    https://pydicom.github.io/pynetdicom/dev/user/ae.html
    AE titles must meet the conditions of a DICOM data element with a Value Representation of AE:
    * Leading and trailing spaces (hex 0x20) are non-significant.
    * Maximum 16 characters (once non-significant characters are removed).
    * Valid characters belong to the DICOM Default Character Repertoire, which is the basic G0 Set
        of the ISO/IEC 646:1991 (ASCII) standard excluding backslash (\ - hex 0x5C) and all control
        characters (such as '\n').
    * An AE title made entirely of spaces is not allowed.
    """
    # Strip leading and trailing spaces (non-significant)
    stripped_title = ae_title.strip()

    # Check length after stripping spaces
    if not (1 <= len(stripped_title) <= 16):
        return False

    # Ensure the title is not entirely spaces
    if not stripped_title:
        return False

    # Define the allowed characters in the DICOM Default Character Repertoire, excluding backslash
    # This includes uppercase letters, digits, and certain punctuation characters
    valid_pattern = r"^[A-Z0-9 _!\"#$%&\'()*+,-./:;<=>?@^_`{|}~]*$"

    # Check if the stripped title only contains valid characters
    return bool(re.fullmatch(valid_pattern, stripped_title))


def test_is_valid_dicom_ae_title() -> bool:
    # Test the function

    success = True
    test_ae_titles = [
        ("MYAE", True),  # Valid
        ("MY_AE_TITLE", True),  # Valid (within 16 characters, valid chars)
        ("LONG_AE_TITLE_12345", False),  # Invalid (more than 16 characters)
        ("INVALID\\TITLE", False),  # Invalid (contains backslash)
        ("   ", False),  # Invalid (entirely spaces)
        ("VALID TITLE", True),  # Valid (has spaces and uppercase)
        ("VALIDTITLE!@#", True),  # Valid (special characters allowed)
        ("LOWERcase", False),  # Invalid (contains lowercase letters)
    ]

    for title_tuple in test_ae_titles:
        valid_response = is_valid_dicom_ae_title(title_tuple[0])
        assert (
            title_tuple[1] == valid_response
        ), f"{title_tuple[0]} assertion failed, response {valid_response}"
        success = title_tuple[1] == valid_response

    return success
