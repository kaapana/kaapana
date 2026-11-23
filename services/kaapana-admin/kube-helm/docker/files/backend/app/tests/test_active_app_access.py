"""Who sees and may end which active application, and which Helm values leave kube-helm.

Runs offline against app.auth_utils only; the route wiring needs a live server.
"""

import base64
import json

import pytest
from starlette.requests import Request

from app.auth_utils import (
    caller_project_ids,
    may_complete_app,
    may_see_app,
    public_values,
    valid_release_name,
)

PROJECT_A = "11111111-1111-1111-1111-111111111111"
PROJECT_B = "22222222-2222-2222-2222-222222222222"


def _token(payload: dict) -> str:
    def part(data: dict) -> str:
        raw = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
        return raw.rstrip("=")

    return f"{part({'alg': 'none'})}.{part(payload)}.signature"


def _request(payload=None) -> Request:
    headers = []
    if payload is not None:
        headers.append((b"x-forwarded-access-token", _token(payload).encode()))
    return Request({"type": "http", "headers": headers})


def _member_of(*project_ids) -> Request:
    return _request(
        {
            "realm_access": {"roles": ["user"]},
            "projects": [{"id": pid, "name": f"p-{pid[:4]}"} for pid in project_ids],
        }
    )


def _app(project: str, from_workflow_run: bool) -> dict:
    return {"project": project, "from_workflow_run": from_workflow_run}


ADMIN_REQUESTS = [
    pytest.param(_request({"realm_access": {"roles": ["admin"]}}), id="realm-role"),
    pytest.param(
        _request({"realm_access": {"roles": []}, "groups": ["/kaapana_admin"]}),
        id="group",
    ),
]


@pytest.mark.parametrize("project", [PROJECT_A, PROJECT_B, ""])
def test_caller_without_token_sees_every_app(project):
    assert may_see_app(_request(), project)


@pytest.mark.parametrize("admin", ADMIN_REQUESTS)
@pytest.mark.parametrize("project", [PROJECT_A, PROJECT_B, ""])
def test_admin_sees_every_app(admin, project):
    assert may_see_app(admin, project)


def test_member_sees_only_own_project_apps():
    member = _member_of(PROJECT_A)
    assert may_see_app(member, PROJECT_A)
    assert not may_see_app(member, PROJECT_B)
    assert not may_see_app(member, "")
    assert not may_see_app(member, None)


@pytest.mark.parametrize(
    "claim",
    [
        pytest.param(None, id="null"),
        pytest.param(PROJECT_A, id="string"),
        pytest.param({"id": PROJECT_A}, id="dict"),
        pytest.param([{"name": "a"}, PROJECT_A, None, {"id": 5}], id="no-ids"),
    ],
)
def test_malformed_projects_claim_sees_nothing(claim):
    request = _request({"realm_access": {"roles": ["user"]}, "projects": claim})
    assert caller_project_ids(request) == set()
    assert not may_see_app(request, PROJECT_A)
    assert not may_see_app(request, "")


def test_missing_projects_claim_sees_nothing():
    request = _request({"realm_access": {"roles": ["user"]}})
    assert caller_project_ids(request) == set()
    assert not may_see_app(request, PROJECT_A)


def test_undecodable_token_sees_nothing():
    request = Request(
        {"type": "http", "headers": [(b"x-forwarded-access-token", b"not-a-jwt")]}
    )
    assert not may_see_app(request, PROJECT_A)
    assert not may_see_app(request, "")


def test_empty_token_header_sees_nothing():
    request = Request({"type": "http", "headers": [(b"x-forwarded-access-token", b"")]})
    assert not may_see_app(request, PROJECT_A)
    assert not may_see_app(request, "")
    assert not may_complete_app(request, _app("", True))


def test_project_header_grants_nothing():
    request = _member_of(PROJECT_A)
    request.scope["headers"].append(
        (b"project", json.dumps({"id": PROJECT_B, "name": "b"}).encode())
    )
    assert not may_see_app(request, PROJECT_B)
    assert not may_complete_app(request, _app(PROJECT_B, True))


def test_public_values_keep_only_extension_params():
    values = {
        "global": {"credentials_minio_password": "x", "oidc_client_secret": "y"},
        "extension_params": {"mode": "fast"},
        "image": "app",
    }
    assert public_values(values) == {"extension_params": {"mode": "fast"}}


@pytest.mark.parametrize("values", [{}, None, {"global": {"a": "b"}}, ["x"]])
def test_public_values_without_extension_params_are_empty(values):
    assert public_values(values) == {}


def test_member_may_complete_own_workflow_app():
    assert may_complete_app(_member_of(PROJECT_A), _app(PROJECT_A, True))


def test_member_may_not_complete_installed_app():
    assert not may_complete_app(_member_of(PROJECT_A), _app(PROJECT_A, False))


def test_member_may_not_complete_other_project_app():
    member = _member_of(PROJECT_A)
    assert not may_complete_app(member, _app(PROJECT_B, True))
    assert not may_complete_app(member, _app("", True))


@pytest.mark.parametrize("admin", ADMIN_REQUESTS)
def test_admin_may_complete_any_app(admin):
    assert may_complete_app(admin, _app(PROJECT_B, False))
    assert may_complete_app(admin, _app("", False))


def test_caller_without_token_may_complete_any_app():
    assert may_complete_app(_request(), _app("", False))


@pytest.mark.parametrize(
    "name",
    [
        "x;id",
        "$(id)",
        "`id`",
        ".*",
        "a|b",
        "Jupyterlab-chart",
        "a" * 54,
        "",
        "-a",
        "a-",
        "a b",
        "a\n",
        "a.b",
        None,
        5,
    ],
)
def test_invalid_release_names(name):
    assert not valid_release_name(name)


@pytest.mark.parametrize(
    "name", ["jupyterlab-chart-abc12345", "a", "a" * 53, "kaapanaint-manual-2024"]
)
def test_valid_release_names(name):
    assert valid_release_name(name)
