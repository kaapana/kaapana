import dataclasses
import os
from fastapi import APIRouter, HTTPException
from typing import List, Mapping, Optional
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakGetError
from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class KaapanaUser:
    idx: str
    name: str

@dataclass
class KaapanaGroup:
    idx: str
    name: str

@dataclass
class KaapanaRole:
    idx: str
    name: str
    description: str


class KaapanaUserService:
    def __init__(self, server_url: str,  username: str, password: str, realm_name : str = "kaapana", user_realm_name : str = "kaapana", verify: bool = False):
        self.server_url = server_url
        self.username = username
        self.password = password
        self.realm_name = realm_name
        self.user_realm_name = user_realm_name
        self.verify = verify
        self._login()

    def _login(self):
        # Option 1 - Use Admin from Master (insecure)
        #keycloak_admin = KeycloakAdmin(server_url="https://localhost/auth/", #server_url="https://localhost/auth/",
        #                               username='admin',
        #                               password='Kaapana2020',
        #                               realm_name="kaapana",
        #                               user_realm_name="master",
        #                               verify=False)
        #

        # Option 2 - Create a User in Kaapana for this
        # 
        # HowTo (Source: https://stackoverflow.com/questions/56743109/keycloak-create-admin-user-in-a-realm)
        # 1. Create a user and set a password
        # 2. Under Roles>Client Roles select `realm-managment` and add all roles `query-*` and `view-*`
        self.keycloak_admin = KeycloakAdmin(server_url=self.server_url,
                                       username=self.username,
                                       password=self.password,
                                       realm_name=self.realm_name,
                                       user_realm_name=self.user_realm_name,
                                       verify=self.verify)

    def get_users(self, username: str = None, group_id: str = None) -> List[KaapanaUser]:
        self._login()
        if username:
            lower_user_name = username.lower()
            result = self.keycloak_admin.get_users(query={"search": lower_user_name})
        elif group_id:
            result = self.keycloak_admin.get_group_members(group_id)
        else:
            result = self.keycloak_admin.get_users({})
        return [KaapanaUser(name=r['username'], idx=r['id']) for r in result]

    def get_user(self, idx: str) -> KaapanaUser:
        self._login()
        try:
          r = self.keycloak_admin.get_user(idx)
        except KeycloakGetError as e:
          return None
        return KaapanaUser(name=r['username'], idx=r['id'])

    def get_groups(self, user_id: str = None) -> List[KaapanaGroup]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_user_groups(user_id)
        else:
            result = self.keycloak_admin.get_groups()

        return [KaapanaGroup(name=r['name'], idx=r['id']) for r in result]

    def get_group(self, idx: str = None) -> KaapanaGroup:
        self._login()
        try:
            r = self.keycloak_admin.get_group(group_id=idx)
        except KeycloakGetError:
            # Group not found
            return None
        return KaapanaGroup(name=r['name'], idx=r['id'])

    def _refresh_token_if_necessary(self):
        pass

    def get_roles(self, user_id: str = None) -> List[KaapanaRole]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_realm_roles_of_user(user_id)
        else:
            result = self.keycloak_admin.get_realm_roles()
        return [KaapanaRole(idx=r['id'], name=r['name'], description=r.get('description', "")) for r in result]


def get_kaapana_user_service():
  # user_service = KaapanaUserService(server_url="https://10.128.128.212/auth/", username="backend", password="asdf")
  #user_service = KaapanaUserService(server_url="https://keycloak-internal-service.kube-system.svc/auth/", username="backend", password="asdf")
  # user_service = KaapanaUserService(server_url="https://keycloak-internal-service.kube-system.svc/auth/", username="admin", password="Kaapana2020")

  mapping = {
    "server_url": "KEYCLOAK_URL",
    "username": "KEYCLOAK_USER",
    "password": "KEYCLOAK_PASSWORD"
  }

  values = {}
  for method_var_name, env_var_name in mapping.items():
    value = os.getenv(env_var_name)
    if not value:
      print(f"{env_var_name} not set")
      return None
    values[method_var_name] = value

  # values = {server_url: "https://internal.keycloack.svc", username: "user", password: "test123"}
  return KaapanaUserService(**values)

user_service = get_kaapana_user_service()


router = APIRouter(tags = ["user"])

@router.get('/roles', response_model=List[KaapanaRole])
async def get_roles():
    """ Returns a list of all realm roles available
    """
    roles = user_service.get_roles()
    return roles

@router.get('/groups', response_model=List[KaapanaGroup])
async def  get_groups():
    """ Returns all existing groups
    """
    groups = user_service.get_groups()
    return groups

@router.get('/groups/{idx}', response_model=KaapanaGroup)
async def  get_group_by_id(idx: str):
    """ Returns a given group
    """
    group = user_service.get_group(idx=idx)
    if not group:
      raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.get('/groups/{idx}/users', response_model=List[KaapanaUser])
async def  get_group_users(idx: str):
    """ Returns the users belonging to a given group
    """
    user = user_service.get_users(group_id=idx)
    return user


@router.get('/', response_model=List[KaapanaUser])
async def get_users(username: Optional[str] = None, group_id: Optional[str] = None):
    """ Returns either all users or a subset matching the parameteres
    """
    users = user_service.get_users(username=username, group_id=group_id)
    return users

@router.get('/{idx}', response_model=KaapanaUser)
async def get_user(idx: str):
    """Returns a specific user of the kaapana platform
    """
    user = user_service.get_user(idx)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get('/{idx}/roles', response_model=List[KaapanaRole])
async def get_user_roles(idx: str):
    """Returns the realm roles belonging to a given user
    """
    roles = user_service.get_roles(user_id=idx)
    return roles

@router.get('/{idx}/groups', response_model=List[KaapanaGroup])
async def  get_user_groups(idx: str):
    """Returns the groups a user belongs to
    """
    groups = user_service.get_groups(user_id=idx)
    return groups
