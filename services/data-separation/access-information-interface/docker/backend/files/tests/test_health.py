"""
Unit test for the AII /health endpoint.

Guards the probe target of the deployment's startup, readiness and liveness
probes: without it Kubernetes marks a still-starting or hung AII Ready and
routes traffic to it during redeploys.
No database or Keycloak: the routers and init scripts are stubbed.
"""

import sys
import types
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

# Make the app package importable and stub the router modules, which need a
# database URL, asyncpg and kaapanapy at import time.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for name in ("app.aii.routes", "app.projects.routes", "app.users.routes"):
    sys.modules.setdefault(name, types.SimpleNamespace(router=APIRouter()))
sys.modules.setdefault("app.init_scripts", types.ModuleType("app.init_scripts"))

from app import main  # noqa: E402


def test_health_endpoint_answers_ok():
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
