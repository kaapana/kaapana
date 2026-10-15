import importlib.util
import sys
from unittest.mock import MagicMock, patch

import airflow  # noqa: F401  # initialises with the real requests, before the mocks

from .utils import KAAPANA_DIR, PLUGIN_DIR, mock_modules

sys.path.insert(0, str(PLUGIN_DIR))
mock_modules()
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator

START_PY = (
    KAAPANA_DIR / "data-processing/kaapana-plugin/processing-containers"
    "/minio-operator/files/start.py"
)


def test_workflow_form_action_does_not_override_minio_action(monkeypatch):
    def capture_env(self, *args, **kwargs):
        self.container_env = kwargs["env_vars"]

    with patch.object(KaapanaBaseOperator, "__init__", capture_env):
        from kaapana.operators.MinioOperator import MinioOperator

        op = MinioOperator(dag="", action="put", bucket_name="bucket")

    # KaapanaBaseOperator.execute() adds every workflow_form key upper-cased to the
    # container env; LocalTaggingOperator's form carries "action".
    form_env = {key.upper(): value for key, value in {"action": "add"}.items()}
    for key, value in {**op.container_env, **form_env}.items():
        monkeypatch.setenv(key, value)

    monkeypatch.setitem(sys.modules, "kaapanapy.logger", MagicMock())
    spec = importlib.util.spec_from_file_location("minio_operator_start", START_PY)
    start = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(start)

    assert start.MinioOperatorArguments().action == "put"
