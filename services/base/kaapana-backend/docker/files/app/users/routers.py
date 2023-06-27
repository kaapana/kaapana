from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from .schemas import KaapanaRole, KaapanaGroup, KaapanaUser
from app.dependencies import get_user_service
from keycloak.exceptions import KeycloakGetError, KeycloakPostError


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
async def post_user(
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
    """Add users to group by id"""
    try:
        for user_idx in users:
            us.group_user_add(user_idx, idx)
    except Exception as e:
        raise e


@router.put("/{idx}/groups", response_model=None)
async def add_users_to_group(
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
async def assign_user_to_roles(
    idx: str, roles: List[dict], us=Depends(get_user_service)
):
    """Assign realm roles to user"""
    try:
        us.assign_realm_roles(idx, roles)
    except Exception as e:
        raise e
