"""The daily cleanup skips the namespace of a project deleted since its run started,
instead of starting a pod there."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Airflow fails to import once mock_modules() has replaced requests.
from airflow.exceptions import AirflowSkipException

from .utils import PLUGIN_DIR, mock_modules

sys.path.insert(0, str(PLUGIN_DIR))
mock_modules()
_globals = sys.modules["kaapana.blueprints.kaapana_global_variables"]
_globals.PLATFORM_PREFIX = "kaapana"
_globals.SERVICES_NAMESPACE = "services"

from kaapana.operators import CleanUpExpiredWorkflowDataOperator as module  # noqa: E402
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator  # noqa: E402

PROJECTS = [
    {"kubernetes_namespace": "kaapana-project-admin"},
    {"kubernetes_namespace": "kaapana-project-1234abcd"},
]


def _operator(namespace):
    with patch.object(KaapanaBaseOperator, "__init__", return_value=None):
        operator = module.CleanUpExpiredWorkflowDataOperator(dag=None)
    operator.namespace = namespace
    return operator


@pytest.fixture
def aii():
    response = MagicMock()
    response.json.return_value = PROJECTS
    with patch.object(module.requests, "get", return_value=response) as get:
        yield get


@pytest.fixture
def base_pre_execute():
    with patch.object(KaapanaBaseOperator, "pre_execute") as pre_execute:
        yield pre_execute


def test_deleted_project_is_skipped(aii, base_pre_execute):
    with pytest.raises(AirflowSkipException, match="kaapana-project-deadbeef"):
        _operator("kaapana-project-deadbeef").pre_execute({})
    assert aii.call_args.args[0] == "http://aii-service.services.svc:8080/projects"


@pytest.mark.parametrize("namespace", ["kaapana-project-1234abcd", "kaapana-project-admin"])
def test_existing_project_is_cleaned(aii, base_pre_execute, namespace):
    _operator(namespace).pre_execute({"run": 1})
    base_pre_execute.assert_called_once_with({"run": 1})


def test_services_namespace_does_not_ask_aii(aii, base_pre_execute):
    _operator("services").pre_execute({})
    aii.assert_not_called()


def test_aii_error_fails_the_task(aii, base_pre_execute):
    aii.return_value.raise_for_status.side_effect = RuntimeError("503")
    with pytest.raises(RuntimeError):
        _operator("kaapana-project-1234abcd").pre_execute({})


def test_execute_is_not_overridden():
    # An overridden execute calling super().execute makes Airflow log a warning.
    assert "execute" not in vars(module.CleanUpExpiredWorkflowDataOperator)
