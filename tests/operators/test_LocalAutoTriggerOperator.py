import json
import sys
from glob import glob as real_glob
from unittest.mock import MagicMock, patch

from attr import dataclass

from .generator import generate_ct
from .utils import PLUGIN_DIR, mock_modules

sys.path.insert(0, str(PLUGIN_DIR))
mock_modules()
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

PROJECT = {"id": "6f1c2a3b-0000-4000-8000-000000000000", "name": "MyProject"}
ADMIN = {"id": "00000000-0000-4000-8000-000000000000", "name": "admin"}


def _aii_get(url):
    # AII resolves the raw tag value; anything else (e.g. lower-cased) is a 404
    known = {"MyProject": PROJECT, "admin": ADMIN}.get(url.rsplit("/", 1)[-1])
    response = MagicMock(ok=known is not None)
    response.json.return_value = known
    return response


@dataclass
class Dag:
    run_id: str
    conf: dict


def test_triggered_conf_carries_project_of_incoming_series(tmp_path):
    rule = tmp_path / "trigger_rule.json"
    rule.write_text(json.dumps([{"search_tags": {}, "dag_ids": {"my-dag": {}}}]))
    generate_ct(
        tmp_path / "run" / "batch" / "series" / "get-input-data" / "ct.dcm",
        {"ClinicalTrialProtocolID": "MyProject"},
    )

    with patch.object(KaapanaPythonBaseOperator, "__init__", lambda *a, **k: None):
        from kaapana.operators import LocalAutoTriggerOperator as module

        op = module.LocalAutoTriggerOperator(dag="")
    op.airflow_workflow_dir = str(tmp_path)
    op.operator_in_dir = "get-input-data"

    def fake_glob(pattern, **kwargs):
        if pattern.endswith("trigger_rule.json"):
            return [str(rule)]
        return real_glob(pattern, **kwargs)

    with patch.object(module, "trigger") as trigger, patch.object(
        module, "requests"
    ) as requests, patch.object(module, "glob", fake_glob):
        requests.get.side_effect = _aii_get
        op.start(ds=None, dag_run=Dag(run_id="run", conf={}))

    assert trigger.call_args.kwargs["dag_id"] == "my-dag"
    assert trigger.call_args.kwargs["conf"]["project_form"] == PROJECT
