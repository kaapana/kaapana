"""Deleting a project deletes its namespace through kube-helm and its system user in
Keycloak, and a failure of either never blocks the project delete."""

import asyncio
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
import requests

# app.database needs asyncpg, which the test environment does not have.
for name in (
    "kaapanapy",
    "kaapanapy.helper",
    "kaapanapy.helper.get_minio_client",
    "kaapanapy.helper.minio_credentials",
    "kaapanapy.logger",
    "kaapanapy.settings",
    "app.database",
):
    sys.modules.setdefault(name, MagicMock())

from app.projects import crud, kubehelm, routes  # noqa: E402
from app.projects.schemas import Project  # noqa: E402

PROJECT = Project(
    id=UUID("1234abcd-0000-4000-8000-000000000000"),
    name="study",
    description="",
)
NAMESPACE = PROJECT.kubernetes_namespace
SYSTEM_USER = f"{NAMESPACE}-system-user"
USER_ID = "4f0c5a1e-system-user-id"
CHART_USER_SECRET = (
    Path(__file__).resolve().parents[5]
    / "project-namespace/project-namespace-chart/templates/project-user-secret.yaml"
)


def _response(status):
    response = requests.Response()
    response.status_code = status
    response._content = b"answer"
    return response


def test_namespace_is_the_projects_own():
    assert NAMESPACE.endswith("-project-1234abcd")


def test_system_user_name_matches_the_chart():
    match = re.search(
        r'printf "%s-%s"\s+\.Values\.global\.project_namespace\s+"([^"]+)"',
        CHART_USER_SECRET.read_text(),
    )
    assert match, "the chart no longer names the user <namespace>-<suffix>"
    assert f"{NAMESPACE}-{match.group(1)}" == SYSTEM_USER
    assert routes.project_system_user_name(PROJECT) == SYSTEM_USER


def test_system_user_roles_are_deleted_in_every_project():
    session = MagicMock(execute=AsyncMock(), commit=AsyncMock())
    asyncio.run(crud.delete_user_roles_in_all_projects(session, USER_ID))
    statement = session.execute.call_args.args[0]
    where = statement.whereclause.compile(compile_kwargs={"literal_binds": True})
    assert statement.table.name == "users_projects_roles"
    assert str(where) == f"users_projects_roles.keycloak_id = '{USER_ID}'"
    session.commit.assert_awaited_once()


def test_posts_the_namespace_to_kube_helm():
    with patch.object(kubehelm.requests, "post", return_value=_response(200)) as post:
        kubehelm.delete_project_namespace(PROJECT)
    post.assert_called_once()
    assert post.call_args.args[0] == f"{kubehelm.kube_helm_api}/delete-namespace"
    assert post.call_args.kwargs["json"] == {"namespace": NAMESPACE}
    assert post.call_args.kwargs["timeout"]


@pytest.mark.parametrize("status", [400, 403, 404, 500])
def test_error_answer_is_only_logged(status, caplog):
    with patch.object(kubehelm.requests, "post", return_value=_response(status)):
        kubehelm.delete_project_namespace(PROJECT)
    assert f"Could not delete namespace {NAMESPACE}" in caplog.text


def test_connection_error_is_only_logged(caplog):
    with patch.object(
        kubehelm.requests, "post", side_effect=requests.ConnectionError("refused")
    ):
        kubehelm.delete_project_namespace(PROJECT)
    assert f"Could not delete namespace {NAMESPACE}" in caplog.text


def _delete(
    project, admin_project=None, crud_delete=None, user_found=True, fails=None
):
    """Run delete_project for `project` and return the steps in the order they ran.

    Keycloak knows the system user unless `user_found` is false; the system-user step
    named by `fails` raises."""
    calls = []
    helper = MagicMock(
        teardown_project=AsyncMock(side_effect=lambda **_: calls.append("teardown"))
    )

    def step(name, result=None):
        def run(*args):
            if fails == name:
                raise requests.ConnectionError(f"{name} failed")
            calls.append((name, *args))
            return result

        return run

    keycloak_client = MagicMock(
        get_user_by_name=MagicMock(
            side_effect=step("lookup", {"id": USER_ID} if user_found else None)
        ),
        delete_user=MagicMock(side_effect=step("delete-user")),
    )
    roles_step = step("roles")

    def crud(*_):
        if crud_delete:
            raise crud_delete
        calls.append("crud")

    with (
        patch.object(routes.crud, "get_projects", AsyncMock(return_value=[project])),
        patch.object(
            routes.crud, "get_admin_project", AsyncMock(return_value=admin_project)
        ),
        patch.object(routes.crud, "delete_project", AsyncMock(side_effect=crud)),
        patch.object(
            routes.crud,
            "delete_user_roles_in_all_projects",
            AsyncMock(side_effect=lambda _session, user_id: roles_step(user_id)),
        ),
        patch.object(
            routes,
            "KeycloakHelper",
            MagicMock(side_effect=step("init", keycloak_client)),
        ),
        patch.object(routes.dicom_data, "get_orphan_series", return_value=[]),
        patch.object(routes.dicom_data, "clear_project_mappings"),
        patch.object(routes.dicom_data, "trigger_delete_series_dag"),
        patch.object(
            routes.kubehelm,
            "uninstall_project_helm_chart",
            side_effect=lambda p: calls.append(("uninstall", p.kubernetes_namespace)),
        ),
        patch.object(
            routes.kubehelm,
            "delete_project_namespace",
            side_effect=lambda p: calls.append(("namespace", p.kubernetes_namespace)),
        ),
    ):
        try:
            response = asyncio.run(
                routes.delete_project(
                    project_id=project.id,
                    session=MagicMock(),
                    opensearch_helper=helper,
                    minio_helper=helper,
                )
            )
        except Exception as e:
            return calls, e
    return calls, response


ADMIN = Project(
    id=UUID("00000000-0000-4000-8000-000000000002"), name="admin", description=""
)
PUBLIC = Project(
    id=UUID("00000000-0000-4000-8000-000000000003"), name="public", description=""
)


def test_namespace_is_deleted_last():
    calls, response = _delete(PROJECT, admin_project=ADMIN)
    assert response.status_code == 204
    assert calls == [
        "teardown",
        "teardown",
        ("uninstall", NAMESPACE),
        "crud",
        ("init",),
        ("lookup", SYSTEM_USER),
        ("roles", USER_ID),
        ("delete-user", USER_ID),
        ("namespace", NAMESPACE),
    ]


def test_missing_system_user_still_deletes_the_project():
    calls, response = _delete(PROJECT, admin_project=ADMIN, user_found=False)
    assert response.status_code == 204
    assert calls[-2:] == [("lookup", SYSTEM_USER), ("namespace", NAMESPACE)]


@pytest.mark.parametrize("step", ["init", "lookup", "roles", "delete-user"])
def test_keycloak_failure_never_blocks_the_project_delete(step, caplog):
    calls, response = _delete(PROJECT, admin_project=ADMIN, fails=step)
    assert response.status_code == 204
    assert calls[-1] == ("namespace", NAMESPACE)
    assert f"Could not delete Keycloak user {SYSTEM_USER}" in caplog.text
    if step == "roles":
        # The user keeps existing, so it can still be found by name later.
        assert ("delete-user", USER_ID) not in calls


def test_failed_database_delete_keeps_the_namespace():
    calls, error = _delete(PROJECT, crud_delete=RuntimeError("foreign key"))
    assert isinstance(error, RuntimeError)
    assert ("namespace", NAMESPACE) not in calls


def test_failed_database_delete_keeps_the_system_user():
    calls, error = _delete(PROJECT, crud_delete=RuntimeError("foreign key"))
    assert isinstance(error, RuntimeError)
    assert calls == ["teardown", "teardown", ("uninstall", NAMESPACE)]


@pytest.mark.parametrize("admin_lookup", [ADMIN, PUBLIC, None])
def test_admin_project_is_refused_before_anything_is_deleted(admin_lookup):
    calls, error = _delete(ADMIN, admin_project=admin_lookup)
    assert isinstance(error, routes.HTTPException)
    assert error.status_code == 403
    assert calls == []
