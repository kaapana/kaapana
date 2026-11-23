"""Deleting a project deletes its namespace through kube-helm, and a failed namespace
delete never blocks the project delete."""

import asyncio
import sys
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

from app.projects import kubehelm, routes  # noqa: E402
from app.projects.schemas import Project  # noqa: E402

PROJECT = Project(
    id=UUID("1234abcd-0000-4000-8000-000000000000"),
    name="study",
    description="",
)
NAMESPACE = PROJECT.kubernetes_namespace


def _response(status):
    response = requests.Response()
    response.status_code = status
    response._content = b"answer"
    return response


def test_namespace_is_the_projects_own():
    assert NAMESPACE.endswith("-project-1234abcd")


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


def _delete(project, admin_project=None, crud_delete=None):
    """Run delete_project for `project` and return the steps in the order they ran."""
    calls = []
    helper = MagicMock(
        teardown_project=AsyncMock(side_effect=lambda **_: calls.append("teardown"))
    )

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
        ("namespace", NAMESPACE),
    ]


def test_failed_database_delete_keeps_the_namespace():
    calls, error = _delete(PROJECT, crud_delete=RuntimeError("foreign key"))
    assert isinstance(error, RuntimeError)
    assert ("namespace", NAMESPACE) not in calls


@pytest.mark.parametrize("admin_lookup", [ADMIN, PUBLIC, None])
def test_admin_project_is_refused_before_anything_is_deleted(admin_lookup):
    calls, error = _delete(ADMIN, admin_project=admin_lookup)
    assert isinstance(error, routes.HTTPException)
    assert error.status_code == 403
    assert calls == []
