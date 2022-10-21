from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from .schemas import KaapanaRole, KaapanaGroup, KaapanaUser
from app.dependencies import get_user_service

router = APIRouter(tags = ["user"])

@router.get('/roles', response_model=List[KaapanaRole])
async def get_roles(us=Depends(get_user_service)):
    """ Returns a list of all realm roles available
    """
    return us.get_roles()

@router.get('/groups', response_model=List[KaapanaGroup])
async def  get_groups(us=Depends(get_user_service)):
    """ Returns all existing groups
    """
    return us.get_groups()

@router.get('/groups/{idx}', response_model=KaapanaGroup)
async def  get_group_by_id(idx: str, us=Depends(get_user_service)):
    """ Returns a given group
    """
    group = us.get_group(idx=idx)
    if not group:
      raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.get('/groups/{idx}/users', response_model=List[KaapanaUser])
async def  get_group_users(idx: str, us=Depends(get_user_service)):
    """ Returns the users belonging to a given group
    """
    return us.get_users(group_id=idx)

@router.get('/', response_model=List[KaapanaUser])
async def get_users(username: Optional[str] = None, group_id: Optional[str] = None, us=Depends(get_user_service)):
    """ Returns either all users or a subset matching the parameteres
    """
    return us.get_users(username=username, group_id=group_id)

@router.get('/{idx}', response_model=KaapanaUser)
async def get_user(idx: str, us=Depends(get_user_service)):
    """Returns a specific user of the kaapana platform
    """
    user = us.get_user(idx)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get('/{idx}/roles', response_model=List[KaapanaRole])
async def get_user_roles(idx: str, us=Depends(get_user_service)):
    """Returns the realm roles belonging to a given user
    """
    return us.get_roles(user_id=idx)

@router.get('/{idx}/groups', response_model=List[KaapanaGroup])
async def  get_user_groups(idx: str, us=Depends(get_user_service)):
    """Returns the groups a user belongs to
    """
    return us.get_groups(user_id=idx)
