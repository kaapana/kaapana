from flask import jsonify, request, abort
from flask import current_app
from . import api_v1

import dataclasses
from typing import List, Optional
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
        r = self.keycloak_admin.get_user(idx)
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

    def get_roles(self, user_id: str) -> List[KaapanaRole]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_realm_roles_of_user(user_id)
        else:
            result = self.keycloak_admin.get_realm_roles()
        print(result)
        return [KaapanaRole(idx=r['id'], name=r['name'], description=r.get('description', "")) for r in result]


# user_service = KaapanaUserService(server_url="https://10.128.128.212/auth/", username="backend", password="asdf")
user_service = KaapanaUserService(server_url="https://keycloak-internal-service.kube-system.svc/auth/", username="backend", password="asdf")


@api_v1.route('/users')
def get_users():
    """ Returns either all users or a subset matching the parameteres
    ---
    tags:
      - auth
    parameters:
      - name: username
        in: query
        type: string
        required: false
      - name: groupid
        in: query
        type: string
        required: false
    definitions:
      User:
        type: object
        properties:
          idx:
            type: string
          name:
            type: string
      Users:
        type: array
        items:
         $ref: '#/definitions/User'
    responses:
      200:
        description: A list of colors (may be filtered by palette)
        schema:
          $ref: '#/definitions/Users'
        examples:
          rgb: ['red', 'green', 'blue']
    """
    users = user_service.get_users(username=request.args.get("username", default=None),
                                   group_id=request.args.get("groupid", default=None))
    return jsonify(users)

@api_v1.route('/users/<idx>')
def get_user(idx: str):
    """Returns a specific user of the kaapana platform
    ---
    tags:
      - auth
    parameters:
      - name: idx
        in: path
        type: string
        required: true
    responses:
      200:
        description: A individual user
        schema:
          $ref: '#/definitions/User'
      404:
        description: If user is not found
    """
    user = user_service.get_user(idx)
    if not user:
        abort(404)
    return jsonify(user)

@api_v1.route('/users/<idx>/roles')
def get_user_roles(idx: str):
    """Returns the realm roles belonging to a given user
    ---
    tags:
      - auth
    parameters:
      - name: idx
        in: path
        type: string
        required: true
    definitions:
      Role:
        type: object
        properties:
          idx:
            type: string
          name:
            type: string
      Roles:
        type: array
        items:
         $ref: '#/definitions/Role'
    responses:
      200:
        description: A list of roles belonging to the given user
        schema:
          $ref: '#/definitions/Roles'
    """
    roles = user_service.get_roles(user_id=idx)
    return jsonify(roles)

@api_v1.route('/users/<idx>/groups')
def get_user_groups(idx: str):
    """Returns the groups a user belongs to
    ---
    tags:
      - auth
    parameters:
      - name: idx
        in: path
        type: string
        required: true
    responses:
      200:
        description: A list of groups the user is member of
        schema:
          $ref: '#/definitions/Groups'
    """
    groups = user_service.get_groups(user_id=idx)
    return jsonify(groups)

@api_v1.route('/roles')
def get_roles():
    """ Returns a list of all realm roles available
    ---
    tags:
     - auth
    responses:
      200:
        description: A list of realm roles on the server
        schema:
          $ref: '#/definitions/Roles'
    """
    roles = user_service.get_roles()
    return jsonify(roles)

@api_v1.route('/groups')
def get_groups():
    """ Returns all existing groups
    ---
    tags:
     - auth
    definitions:
      Group:
        type: object
        properties:
          idx:
            type: string
          name:
            type: string
      Groups:
        type: array
        items:
         $ref: '#/definitions/Group'
    responses:
      200:
        description: A list of groups on the server
        schema:
          $ref: '#/definitions/Groups'
    """
    groups = user_service.get_groups()
    return jsonify(groups)

@api_v1.route('/groups/<idx>')
def get_group_by_id(idx: str):
    """ Returns a given group
    ---
    tags:
     - auth
    parameters:
     - name: idx
       in: path
       type: string
       required: true
    responses:
      200:
        description: The requested group
        schema:
          $ref: '#/definitions/Group'
      404:
        description: Group was not found
    """
    group = user_service.get_group(idx=idx)
    if not group:
        abort(404)
    return jsonify(group)


@api_v1.route('/groups/<idx>/users')
def get_group_users(idx: str):
    """ Returns the users belonging to a given group
    ---
    tags:
     - auth
    parameters:
     - name: idx
       in: path
       type: string
       required: true
    responses:
      200:
        description: A list of users belongig to the given group
        schema:
          $ref: '#/definitions/Users'
    """
    user = user_service.get_users(group_id=idx)
    return jsonify(user)
