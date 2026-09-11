import os
import sys
from pathlib import Path

import pytest
from starlette.requests import Request

# app.config reads these at import time via os.environ[...]; nothing in the
# import chain opens a connection, so dummy values are enough.
os.environ.setdefault("DICOMWEB_BASE_URL", "http://dcm4chee/dcm4chee-arc/aets/KAAPANA")
os.environ.setdefault("DICOMWEB_BASE_URL_WADO_URI", "http://dcm4chee/dcm4chee-arc")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("ACCESS_INFORMATION_INTERFACE_URL", "http://aii")
os.environ.setdefault("DWF_IDENTITY_OPENID_CONFIG_URL", "http://keycloak/openid-config")
os.environ.setdefault("DWF_IDENTITY_OPENID_CLIENT_ID", "kaapana")

# Make `app` importable whatever directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def make_request():
    """Build the minimal ASGI scope the project-scope helpers read."""

    def _make_request(header: str | None = None, *, admin: bool = False, projects: list[str]) -> Request:
        headers = [(b"project", header.encode())] if header is not None else []
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "query_string": b"",
                "headers": headers,
                "token": {"projects": [{"id": p} for p in projects]},
                "admin": admin,
            }
        )

    return _make_request
