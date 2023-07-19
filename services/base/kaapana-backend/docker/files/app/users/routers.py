from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from .schemas import KaapanaRole, KaapanaGroup, KaapanaUser, KaapanaProject
from app.dependencies import get_user_service, get_db
from keycloak.exceptions import KeycloakGetError, KeycloakPostError
from sqlalchemy.orm import Session
from app.users import crud, models

router = APIRouter(tags=["users"])


@router.get("/roles", response_model=List[KaapanaRole])
async def get_roles(us=Depends(get_user_service)):
    """Returns a list of all realm roles available"""
    return us.get_roles()


@router.get("/groups", response_model=List[KaapanaGroup])
async def get_groups(us=Depends(get_user_service)):
    """Returns all existing groups"""
    return us.get_groups()


@router.get("/groups/{idx}", response_model=KaapanaGroup)
async def get_group_by_id(idx: str, us=Depends(get_user_service)):
    """Returns a given group"""
    group = us.get_group(idx=idx)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get("/groups/{idx}/users", response_model=List[KaapanaUser])
async def get_group_users(idx: str, us=Depends(get_user_service)):
    """Returns the users belonging to a given group"""
    return us.get_users(group_id=idx)


@router.get("/groups/{idx}/roles", response_model=List[KaapanaRole])
async def get_group_users(idx: str, us=Depends(get_user_service)):
    """Returns the roles belonging to a given group"""
    return us.get_roles(group_id=idx)


@router.get("/", response_model=List[KaapanaUser])
async def get_users(
    username: Optional[str] = None,
    group_id: Optional[str] = None,
    us=Depends(get_user_service),
):
    """Returns either all users or a subset matching the parameteres"""
    return us.get_users(username=username, group_id=group_id)


@router.get("/{idx}", response_model=KaapanaUser)
async def get_user(idx: str, us=Depends(get_user_service)):
    """Returns a specific user of the kaapana platform"""
    user = us.get_user(idx)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{idx}/roles", response_model=List[KaapanaRole])
async def get_user_roles(idx: str, us=Depends(get_user_service)):
    """Returns the realm roles belonging to a given user"""
    return us.get_roles(user_id=idx)


@router.get("/{idx}/groups", response_model=List[KaapanaGroup])
async def get_user_groups(idx: str, us=Depends(get_user_service)):
    """Returns the groups a user belongs to"""
    return us.get_groups(user_id=idx)


@router.post("/", response_model=KaapanaUser)
async def post_user(
    username: str,
    email="",
    firstName="",
    lastName="",
    attributes={},
    us=Depends(get_user_service),
):
    """Create a new user with username"""
    try:
        return us.post_user(
            username=username, email=email, firstName=firstName, lastName=lastName
        )
    except KeycloakPostError as e:
        raise HTTPException(status_code=409, detail="Username already exists.")


@router.post("/groups", response_model=KaapanaGroup)
async def post_group(
    groupname: str,
    us=Depends(get_user_service),
):
    """Create a new group with groupname"""
    try:
        return us.post_group(groupname=groupname)
    except KeycloakPostError as e:
        raise HTTPException(status_code=409, detail="Group already exists.")


@router.put("/groups/{idx}/users", response_model=None)
async def add_users_to_group(
    idx: str,
    users: List[str],
    us=Depends(get_user_service),
):
    """Add multiple users to group by id"""
    try:
        for user_idx in users:
            us.group_user_add(user_idx, idx)
    except Exception as e:
        raise e


@router.put("/groups/{idx}/roles", response_model=None)
async def assign_roles_to_group(
    idx: str,
    roles: List[dict],
    us=Depends(get_user_service),
):
    """Assign realm roles to group"""
    kaapana_roles = [
        KaapanaRole(
            idx=r.get("idx"), name=r.get("name"), description=r.get("description")
        )
        for r in roles
    ]
    try:
        us.assign_group_realm_roles(idx, kaapana_roles)
    except Exception as e:
        raise e


@router.put("/{idx}/groups", response_model=None)
async def add_user_to_groups(
    idx: str,
    groups: List[str],
    us=Depends(get_user_service),
):
    """Add user to multiple groups by id"""
    try:
        for group_idx in groups:
            us.group_user_add(idx, group_idx)
    except Exception as e:
        raise e


@router.put("/{idx}/roles", response_model=None)
async def assign_role_to_user(
    idx: str, roles: List[dict], us=Depends(get_user_service)
):
    """Assign realm roles to user"""
    kaapana_roles = [
        KaapanaRole(
            idx=r.get("idx"), name=r.get("name"), description=r.get("description")
        )
        for r in roles
    ]
    try:
        us.assign_realm_roles(idx, kaapana_roles)
    except Exception as e:
        raise e


@router.get("/roles/{name}", response_model=KaapanaRole)
async def get_realm_role_by_name(name: str, us=Depends(get_user_service)):
    """Get realm information by name"""
    try:
        return us.get_realm_role_by_name(name)
    except Exception as e:
        raise e


@router.post("/roles/{name}", response_model=KaapanaRole)
async def post_realm_role(
    name: str, description: str = "", us=Depends(get_user_service)
):
    """Create a new realm role"""
    payload = {"name": name, "description": description}
    try:
        return us.create_realm_role(payload)
    except Exception as e:
        raise e


@router.get("/projects/", response_model=List[KaapanaProject])
async def get_project(name: str = "", db: Session = Depends(get_db)):
    return crud.get_project(db, name)


@router.delete("/projects/{name}", response_model=None)
async def delete_project(
    name: str, us=Depends(get_user_service), db: Session = Depends(get_db)
):
    pass


@router.post("/projects/{name}", response_model=KaapanaProject)
async def post_project(
    name: str, us=Depends(get_user_service), db: Session = Depends(get_db)
):
    """
    Create a new project.

    Creates keycloak group and roles for the project.
    Creates a database object for the project in the kaapana-backend database.
    """
    project_group = us.post_group(name)
    roles2idx = {"role_admin": None, "role_member": None}
    for role_name in roles2idx.keys():
        payload = {
            "name": name + "_" + role_name,
            "description": f"{role_name} for {name}",
        }
        realm_role = us.create_realm_role(payload)
        roles2idx[role_name] = realm_role.idx

        if role_name == "role_member":
            payload["idx"] = realm_role.idx
            roles = [payload]
            us.assign_group_realm_roles(project_group.idx, roles)

    kaapana_project = KaapanaProject(
        name=name,
        role_admin_idx=roles2idx.get("role_admin"),
        role_member_idx=roles2idx.get("role_member"),
        group_idx=project_group.idx,
    )

    return crud.create_project(db=db, kaapana_project=kaapana_project)


@router.put("/projects/{name}/users/", response_model=KaapanaProject)
async def put_project(
    name: str,
    users: List[str],
    us=Depends(get_user_service),
    db: Session = Depends(get_db),
):
    """
    Add members to a project.

    Add members to project group
    """
    kaapana_project = crud.get_project(db, name)

    for user in users:
        us.add_user_group(kaapana_project.group_idx, user)
