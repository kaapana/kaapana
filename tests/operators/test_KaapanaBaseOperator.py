import os
import re
import sys
from unittest.mock import MagicMock, patch

# Imported before mock_modules() swaps requests for a mock, so airflow's lazy
# `from requests.exceptions import ...` still finds the real submodule.
import requests  # noqa: F401

from .utils import PLUGIN_DIR, mock_modules

sys.path.insert(0, str(PLUGIN_DIR))
mock_modules()
from kaapana.operators import KaapanaBaseOperator as base_operator_module
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator

PROCESSING_WORKFLOW_DIR = "/kaapana/mounted/workflows"


class _Operator(KaapanaBaseOperator):
    # Skip the real constructor; only create_conf_configmap is under test.
    def __init__(self, **kwargs):
        pass


def test_conf_configmap_is_mounted_into_the_raw_run_directory():
    # Airflow's own run_ids carry characters that cure_invalid_name strips. The mount must
    # still land in the directory WORKFLOW_DIR points the processing container at.
    run_id = "scheduled__2026-09-10T00:00:00+00:00"
    op = _Operator()
    op.namespace, op.volumes, op.volume_mounts = "project-admin", [], []
    context = {"run_id": run_id, "dag_run": MagicMock(conf={})}

    with patch.multiple(
        base_operator_module,
        PROCESSING_WORKFLOW_DIR=PROCESSING_WORKFLOW_DIR,
        cure_invalid_name=lambda name, regex: re.sub(r"[^-a-z0-9]", "", name),
    ):
        op.create_conf_configmap(context)

    mount_path = base_operator_module.client.V1VolumeMount.call_args.kwargs["mount_path"]
    assert mount_path == os.path.join(PROCESSING_WORKFLOW_DIR, run_id, "conf", "conf.json")
