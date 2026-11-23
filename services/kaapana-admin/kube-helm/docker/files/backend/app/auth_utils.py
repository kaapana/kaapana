import base64
import json
import re
from enum import Enum
from typing import Optional

from fastapi import Request


class UserRole(str, Enum):
    """User roles in the Kaapana system."""
    ADMIN = "admin"
    PROJECT_MANAGER = "project-manager"
    PRINCIPAL_INVESTIGATOR = "principal-investigator"


def decode_jwt_payload(raw_token: Optional[str]) -> dict:
    """Decode JWT payload without signature verification for trusted internal headers."""
    if not raw_token:
        return {}
    try:
        parts = raw_token.split(".")
        if len(parts) < 2:
            return {}
        payload_part = parts[1]
        payload_part += "=" * (-len(payload_part) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_part).decode("utf-8"))
    except Exception:
        return {}


def get_request_user_id(request: Request) -> Optional[str]:
    user_id = request.headers.get("x-forwarded-user")
    if user_id:
        return user_id
    token_payload = decode_jwt_payload(request.headers.get("x-forwarded-access-token"))
    return token_payload.get("sub")


def is_admin_request(request: Request) -> bool:
    token_payload = decode_jwt_payload(request.headers.get("x-forwarded-access-token"))
    roles = token_payload.get("realm_access", {}).get("roles", [])
    # Check for admin role or admin group
    if UserRole.ADMIN.value in roles:
        return True
    groups = token_payload.get("groups", [])
    return any('kaapana_admin' in g for g in groups)


# Helm's release-name rule minus the dots, which Kaapana's generated names never have.
_RELEASE_NAME_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?")


def has_access_token(request: Request) -> bool:
    # Present but empty or invalid still counts as a token, so it fails closed.
    return "x-forwarded-access-token" in request.headers


def caller_project_ids(request: Request) -> set:
    """Ids from the token's `projects` claim; anything malformed counts as no project."""
    token_payload = decode_jwt_payload(request.headers.get("x-forwarded-access-token"))
    projects = token_payload.get("projects")
    if not isinstance(projects, list):
        return set()
    return {
        project["id"]
        for project in projects
        if isinstance(project, dict)
        and isinstance(project.get("id"), str)
        and project["id"]
    }


def _has_full_access(request: Request) -> bool:
    # The gateway lets only requests with a token reach kube-helm, so a request
    # without one comes from inside the cluster.
    return not has_access_token(request) or is_admin_request(request)


def may_see_app(request: Request, project: Optional[str]) -> bool:
    if _has_full_access(request):
        return True
    # Membership comes from the token, never from the Project header: that one is
    # built from a client cookie.
    return bool(project) and project in caller_project_ids(request)


def may_complete_app(request: Request, app) -> bool:
    if _has_full_access(request):
        return True
    # Non-admins end only the apps their projects' workflow runs started.
    return may_see_app(request, app["project"]) and bool(app["from_workflow_run"])


def public_values(values: Optional[dict]) -> dict:
    """The part of an app's Helm values a caller may see: the user's parameters only."""
    if isinstance(values, dict) and "extension_params" in values:
        return {"extension_params": values["extension_params"]}
    return {}


def valid_release_name(name) -> bool:
    return (
        isinstance(name, str)
        and len(name) <= 53
        and _RELEASE_NAME_PATTERN.fullmatch(name) is not None
    )
