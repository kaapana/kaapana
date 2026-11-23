"""/delete-namespace: which namespaces kube-helm refuses, and how Kubernetes answers
map to HTTP status codes. Runs without a cluster; CoreV1Api is mocked."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

for key, value in {
    "SECRET_KEY": "x",
    "APPLICATION_ROOT": "/",
    "HELM_EXTENSIONS_CACHE": "/tmp",
    "HELM_PLATFORMS_CACHE": "/tmp",
    "KAAPANA_COLLECTIONS": "x",
    "HELM_NAMESPACE": "admin",
    "RELEASE_NAME": "x",
    "REGISTRY_URL": "x",
    "KUBECTL_PATH": "kubectl",
    "HELM_PATH": "helm",
    "CONTAINERD_SOCK": "x",
}.items():
    os.environ.setdefault(key, value)

# Present in the image, not in a plain test environment.
for name in ("kaapanapy", "kaapanapy.logger", "distutils", "distutils.version"):
    sys.modules.setdefault(name, MagicMock())

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from kubernetes.client.rest import ApiException  # noqa: E402

from app import utils  # noqa: E402

NAMESPACE = "kaapana-project-1234abcd"


@pytest.fixture
def core_v1():
    api = MagicMock()
    with (
        patch.object(utils, "ensure_k8s_config"),
        patch.object(utils.client, "CoreV1Api", return_value=api),
    ):
        yield api


@pytest.fixture
def http(core_v1):
    sys.modules.setdefault("aiofiles", MagicMock())
    sys.modules.setdefault("aiofiles.os", MagicMock())
    from app import routes

    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_deletes_without_waiting(core_v1):
    assert "Started deleting" in utils.delete_namespace(NAMESPACE)
    core_v1.delete_namespace.assert_called_once_with(NAMESPACE)


def test_missing_namespace_counts_as_deleted(core_v1):
    core_v1.delete_namespace.side_effect = ApiException(status=404)
    assert "already gone" in utils.delete_namespace(NAMESPACE)


def test_namespace_being_deleted_counts_as_deleted(core_v1):
    core_v1.delete_namespace.side_effect = ApiException(status=409)
    assert "already being deleted" in utils.delete_namespace(NAMESPACE)


def test_refuses_the_configured_helm_namespace(core_v1):
    with patch.object(utils.settings, "helm_namespace", "charts"):
        with pytest.raises(utils.NamespaceDeleteRefused):
            utils.delete_namespace("charts")
    core_v1.delete_namespace.assert_not_called()


def test_forbidden_is_its_own_error(core_v1):
    core_v1.delete_namespace.side_effect = ApiException(status=403)
    with pytest.raises(utils.NamespaceDeleteForbidden):
        utils.delete_namespace(NAMESPACE)


def test_other_api_errors_are_raised(core_v1):
    core_v1.delete_namespace.side_effect = ApiException(status=500)
    with pytest.raises(ApiException):
        utils.delete_namespace(NAMESPACE)


@pytest.mark.parametrize(
    "namespace", ["admin", "default", "kube-system", "kube-public", "", None, 3]
)
def test_refuses_protected_or_invalid_names(core_v1, namespace):
    with pytest.raises(utils.NamespaceDeleteRefused):
        utils.delete_namespace(namespace)
    core_v1.delete_namespace.assert_not_called()


@pytest.mark.parametrize(
    "side_effect, status",
    [
        (None, 200),
        (ApiException(status=404), 200),
        (ApiException(status=409), 200),
        (ApiException(status=403), 403),
        (ApiException(status=500), 500),
    ],
)
def test_route_status_codes(http, core_v1, side_effect, status):
    core_v1.delete_namespace.side_effect = side_effect
    response = http.post("/delete-namespace", json={"namespace": NAMESPACE})
    assert response.status_code == status


@pytest.mark.parametrize("payload", [{}, {"namespace": "admin"}, {"namespace": "kube-system"}])
def test_route_rejects_bad_requests(http, core_v1, payload):
    response = http.post("/delete-namespace", json=payload)
    assert response.status_code == 400
    core_v1.delete_namespace.assert_not_called()
