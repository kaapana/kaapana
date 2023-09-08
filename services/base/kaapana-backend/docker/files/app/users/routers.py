from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from .schemas import (
    KaapanaRole,
    KaapanaGroup,
    KaapanaUser,
    KaapanaProject,
    ProjectUser,
    ProjectRole,
    AccessTable,
    AccessListEntree,
)
from app.dependencies import get_user_service, get_db, my_get_db
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


@router.get("/groups/{id}", response_model=KaapanaGroup)
async def get_group_by_id(id: str, us=Depends(get_user_service)):
    """Returns a given group"""
    group = us.get_group(id=id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.delete("/groups/{id}", response_model=None)
async def delete_group_by_id(id: str, us=Depends(get_user_service)):
    """Delete group by group id"""
    try:
        return us.delete_group(id)
    except Exception as e:
        raise e


@router.get("/groups/{id}/users", response_model=List[KaapanaUser])
async def get_group_users(id: str, us=Depends(get_user_service)):
    """Returns the users belonging to a given group"""
    return us.get_users(group_id=id)


@router.get("/groups/{id}/roles", response_model=List[KaapanaRole])
async def get_group_users(id: str, us=Depends(get_user_service)):
    """Returns the roles belonging to a given group"""
    return us.get_roles(group_id=id)


@router.get("/", response_model=List[KaapanaUser])
async def get_users(
    username: Optional[str] = None,
    group_id: Optional[str] = None,
    us=Depends(get_user_service),
):
    """Returns either all users or a subset matching the parameteres"""
    return us.get_users(username=username, group_id=group_id)


@router.get("/{id}", response_model=KaapanaUser)
async def get_user(id: str, us=Depends(get_user_service)):
    """Returns a specific user of the kaapana platform"""
    user = us.get_user(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{id}/roles", response_model=List[KaapanaRole])
async def get_user_roles(id: str, us=Depends(get_user_service)):
    """Returns the realm roles belonging to a given user"""
    return us.get_roles(user_id=id)


@router.get("/{id}/groups", response_model=List[KaapanaGroup])
async def get_user_groups(id: str, us=Depends(get_user_service)):
    """Returns the groups a user belongs to"""
    return us.get_groups(user_id=id)


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


@router.put("/groups/{id}/users", response_model=None)
async def add_users_to_group(
    id: str,
    users: List[str],
    us=Depends(get_user_service),
):
    """Add multiple users to group by id"""
    try:
        for user_id in users:
            us.group_user_add(user_id, id)
    except Exception as e:
        raise e


@router.put("/groups/{id}/roles", response_model=None)
async def assign_roles_to_group(
    id: str,
    roles: List[dict],
    us=Depends(get_user_service),
):
    """Assign realm roles to group"""
    kaapana_roles = [
        KaapanaRole(
            id=r.get("id"), name=r.get("name"), description=r.get("description")
        )
        for r in roles
    ]
    try:
        us.assign_group_realm_roles(id, kaapana_roles)
    except Exception as e:
        raise e


@router.put("/{id}/groups", response_model=None)
async def add_user_to_groups(
    id: str,
    groups: List[str],
    us=Depends(get_user_service),
):
    """Add user to multiple groups by id"""
    try:
        for group_id in groups:
            us.group_user_add(id, group_id)
    except Exception as e:
        raise e


@router.put("/{id}/roles", response_model=None)
async def assign_role_to_user(id: str, roles: List[dict], us=Depends(get_user_service)):
    """Assign realm roles to user"""
    kaapana_roles = [
        KaapanaRole(
            id=r.get("id"), name=r.get("name"), description=r.get("description")
        )
        for r in roles
    ]
    try:
        us.assign_realm_roles(id, kaapana_roles)
    except Exception as e:
        raise e


@router.delete("/{id}/roles/{name}", response_model=None)
async def remove_role_from_user(id: str, name: str, us=Depends(get_user_service)):
    """Remove realm roles to user"""
    try:
        us.delete_realm_roles_of_user(id, [name])
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


@router.delete("/roles/{name}", response_model=None)
async def post_realm_role(name: str, us=Depends(get_user_service)):
    """Delete realm role"""
    try:
        return us.delete_realm_role(name)
    except Exception as e:
        raise e


@router.get("/projects/", response_model=List[KaapanaProject])
async def get_project(name: str = "", db: Session = Depends(my_get_db)):
    """
    Get information about all project or a specific project
    """
    return crud.get_project(db, name)


@router.get("/projects/{name}/users", response_model=List[ProjectUser])
async def get_project_users(
    name: str = "", us=Depends(get_user_service), db: Session = Depends(get_db)
):
    """
    Get project specific information about all users in a project.
    """

    def get_project_role(
        user_roles: List[KaapanaRole], project: KaapanaProject
    ) -> ProjectRole:
        """
        Get project role of the user
        """
        for project_role in project.project_roles:
            for user_role in user_roles:
                if user_role.id == project_role.get("id", None):
                    return ProjectRole(
                        project_role_name=project_role.get("project_role_name"),
                        **user_role.dict(),
                    )
        return None

    project = crud.get_project(db, name)[0]
    members = us.get_users(group_id=project.group_id)
    project_users = []
    for user in members:
        user_roles = us.get_roles(user_id=user.id)
        projectRole = get_project_role(user_roles, project)
        if not projectRole:
            raise AssertionError
        project_users.append(ProjectUser(projectRole=projectRole, **user.dict()))

    return project_users


@router.delete("/projects/{name}/users/{id}")
async def remove_user_from_project(
    name: str,
    id: str,
    us=Depends(get_user_service),
    db: Session = Depends(get_db),
) -> None:
    """
    Remove user from project.

    Remove user from project group.
    Remove all project roles from the user for this project.
    """
    kaapana_project = crud.get_project(db, name)[0]
    us.group_user_remove(id, kaapana_project.group_id)
    project_roles = kaapana_project.project_roles
    for role in project_roles:
        if role.get("project_role_name") == "default":
            pass
        else:
            try:
                us.delete_realm_roles_of_user(id, [role.get("name")])
            except Exception as e:
                pass


@router.delete("/projects/{name}", response_model=None)
async def delete_project(
    name: str, us=Depends(get_user_service), db: Session = Depends(get_db)
):
    kaapana_project = crud.get_project(db, name)[0]

    ### Delete realm roles in keycloak
    for project_role in kaapana_project.project_roles:
        us.delete_realm_role(project_role.get("name"))

    ### Delete group in keycloak
    us.delete_group(kaapana_project.group_id)

    ### Delete project from database
    crud.delete_kaapana_project(db=db, kaapana_project=kaapana_project)


@router.post("/projects/{name}", response_model=KaapanaProject)
async def post_project(
    request: Request,
    name: str,
    us=Depends(get_user_service),
    db: Session = Depends(get_db),
):
    """
    Create a new project.

    Creates keycloak group and roles for the project.
    Creates a database object for the project in the kaapana-backend database.
    """
    project_group = us.post_group(name)
    project_role_names = ["admin", "user", "default"]
    project_roles = []
    roles2id = {}
    for project_role_name in project_role_names:
        payload = {
            "name": name + "_" + project_role_name,
            "description": f"{project_role_name} role for project {name}",
        }
        realm_role = us.create_realm_role(payload)
        roles2id[project_role_name] = realm_role.id
        project_roles.append(
            ProjectRole(
                id=realm_role.id,
                name=payload["name"],
                description=payload["description"],
                project_role_name=project_role_name,
            )
        )

        if project_role_name == "default":
            roles = [
                KaapanaRole(
                    id=realm_role.id,
                    name=payload["name"],
                    description=payload["description"],
                )
            ]
            us.assign_group_realm_roles(project_group.id, roles)

    kaapana_project = KaapanaProject(
        name=name,
        group_id=project_group.id,
        project_roles=[
            project_role.__dict__ for project_role in project_roles
        ],  ### I cannot use classes as ColumnType in models
        accesstable_primary_key=name,
    )

    access_table = AccessTable(
        object_primary_key=kaapana_project.name,
    )
    access_table = crud.create_access_table(db=db, accesstable=access_table)

    kaapana_project = crud.create_project(db=db, kaapana_project=kaapana_project)

    ### Create permissions for creator
    if "x-forwarded-preferred-username" in request.headers:
        user = request.headers["x-forwarded-preferred-username"]
    else:
        AssertionError

    crud.create_access_list_entree(
        db=db,
        user=user,
        permissions="rwx",
        accesstable_primary_key=kaapana_project.name,
    )

    return kaapana_project


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
        us.add_user_group(kaapana_project.group_id, user)


@router.put("/projects/{name}/user/{id}/role/{project_role_name}", response_model=None)
async def put_project_user_role(
    name: str,
    id: str,
    project_role_name: str,
    us=Depends(get_user_service),
    db: Session = Depends(get_db),
):
    """
    Change project role for user

    Delete previous project role
    """
    kaapana_project = crud.get_project(db, name)[0]
    project_roles = kaapana_project.project_roles
    for role in project_roles:
        if role.get("project_role_name") == "default":
            pass
        elif role.get("project_role_name") == project_role_name:
            us.assign_realm_roles(id, [ProjectRole(**role)])
        else:
            try:
                us.delete_realm_roles_of_user(id, [role.get("name")])
            except Exception as e:
                pass
