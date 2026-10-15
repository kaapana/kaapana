import importlib.util
import sys
from unittest.mock import MagicMock

from ..operators.utils import KAAPANA_DIR

DAG_FILE = (
    KAAPANA_DIR / "data-processing/processing-pipelines/total-segmentator-v2"
    "/extension/docker/files/dag_total_segmentator_v2.py"
)


def test_each_subtask_run_checks_the_modality_of_its_task(monkeypatch):
    for name in [
        "kaapana",
        "kaapana.operators",
        "kaapana.operators.KaapanaPythonBaseOperator",
        "kaapana.operators.LocalDagTriggerOperator",
        "totalsegmentatorv2",
        "totalsegmentatorv2.GetZenodoModelOperator",
    ]:
        monkeypatch.setitem(sys.modules, name, MagicMock())
    spec = importlib.util.spec_from_file_location("dag_ts_v2", DAG_FILE)
    dag_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dag_module)

    trigger = sys.modules["kaapana.operators.LocalDagTriggerOperator"]
    forms = [
        call.kwargs["extra_conf"]["workflow_form"]
        for call in trigger.LocalDagTriggerOperator.call_args_list
    ]
    modality = {form["TASK"]: form.get("input") for form in forms}
    assert modality["total"] == "CT"
    assert modality["total_mr"] == "MR"
    assert "input" not in dag_module.ui_forms["workflow_form"]["required"]
