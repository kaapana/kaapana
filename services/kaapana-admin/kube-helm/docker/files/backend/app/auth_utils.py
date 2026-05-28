import base64
import json
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
