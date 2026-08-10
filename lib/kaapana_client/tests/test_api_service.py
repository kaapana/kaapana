"""URL project scoping of KaapanaApiService.

Project scope is carried in the URL (``/project/<id>/<service>/...``): the
gateway resolves the id, authorizes the caller against it and injects the
trusted ``Project`` header. The legacy ``Project`` cookie is read by nothing.
Both halves are pinned here — the prefix goes on exactly the project-scoped
services, and no cookie is sent by any verb.
"""

import time

import pytest

from kaapana_client.services import ApiService
from kaapana_client.services.ApiService import KaapanaApiService

ROOT_URL = "https://kaapana.example"
PROJECT_ID = "d7e991b3-9463-48e7-98c2-661da8b83018"
SCOPED_ENDPOINT = "kaapana-backend/client/datasets"
VERBS = ["get", "post", "put", "delete", "head"]


@pytest.fixture
def api():
    """A service with its network-touching ``__init__`` bypassed."""
    service = KaapanaApiService.__new__(KaapanaApiService)
    service.root_url = ROOT_URL
    service.project_id = PROJECT_ID
    service.token = {"access_token": "test-token"}
    service._token_expiry = time.time() + 3600
    return service


@pytest.fixture
def recorded_calls(monkeypatch):
    """Record the kwargs every ``requests.<verb>`` call is made with."""
    calls = []

    def record(**kwargs):
        calls.append(kwargs)
        return "response"

    for verb in VERBS:
        monkeypatch.setattr(ApiService.requests, verb, record)
    return calls


@pytest.mark.parametrize(
    "endpoint",
    [
        "kaapana-backend/client/datasets",
        "kube-helm-api/extensions",
        "workflow-api/v1/workflow-runs",
        "dicom-web-filter/studies",
        # Tolerated, though the documented form has no leading slash.
        "/kaapana-backend/client/datasets",
    ],
)
def test_project_scoped_services_are_prefixed(api, endpoint):
    assert api._url_for(endpoint) == (
        f"{ROOT_URL}/project/{PROJECT_ID}/{endpoint.lstrip('/')}"
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        # No /project/<id>/ IngressRoute exists for these, so a prefix would 404.
        "aii/projects",
        "auth/realms/kaapana/.well-known/openid-configuration",
        "portal-api/menu",
        # A service name that merely starts with a scoped one's must not match.
        "workflow-api-docs/index.html",
    ],
)
def test_unscoped_services_are_not_prefixed(api, endpoint):
    assert api._url_for(endpoint) == f"{ROOT_URL}/{endpoint}"


def test_an_endpoint_that_carries_its_own_prefix_is_left_alone(api):
    """A caller may address any project it may access by writing the prefix."""
    endpoint = f"project/11111111/{SCOPED_ENDPOINT}"
    assert api._url_for(endpoint) == f"{ROOT_URL}/{endpoint}"


@pytest.mark.parametrize("verb", VERBS)
def test_every_verb_scopes_its_url(api, recorded_calls, verb):
    getattr(api, verb)(SCOPED_ENDPOINT)
    assert recorded_calls[0]["url"] == (
        f"{ROOT_URL}/project/{PROJECT_ID}/{SCOPED_ENDPOINT}"
    )


@pytest.mark.parametrize("verb", VERBS)
def test_no_verb_sends_a_cookie(api, recorded_calls, verb):
    """The removal itself: nothing reads a ``Project`` cookie any more."""
    getattr(api, verb)(SCOPED_ENDPOINT)
    assert "cookies" not in recorded_calls[0]
