from datetime import datetime, timedelta
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from attr import dataclass
import pytest


from airflow.models.skipmixin import SkipMixin
from airflow.operators.python import PythonOperator

from .utils import mock_modules, PLUGIN_DIR, DICOM_TAG_DICT
from .generator import generate_ct, generate_rtstruct, generate_seg

sys.path.insert(0, str(PLUGIN_DIR))
mock_modules()
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


def __init__(self, *args, **kwargs):
    pass


@dataclass
class Dag:
    run_id: str


AIRFLOW_WORKFLOW_DIR = "tests/airflow_workflow_dir"
OPERATOR_IN_DIR = "operator_in_dir"
OPERATOR_OUT_DIR = "operator_out_dir"
BATCH_NAME = "batch_name"
DAG_RUN_ID = "dag_run_id"


@pytest.fixture
def op(request):
    # Default parameters
    marker = request.node.get_closest_marker("dcm_params")
    if marker is None:
        params = {}
    else:
        params = marker.args[0]

    os.environ["DICT_PATH"] = str(DICOM_TAG_DICT)

    dag = Dag(run_id=DAG_RUN_ID)

    def mock_decorator_function(func):
        def wrapper(*args, **kwargs):
            result = func(dag_run=dag, *args, **kwargs)
            return result

        return wrapper

    mock1 = patch.object(KaapanaPythonBaseOperator, "__init__", __init__)
    mock2 = patch.object(SkipMixin, "__init__", __init__)
    mock3 = patch.object(PythonOperator, "__init__", __init__)
    mock4 = patch(
        "kaapana.operators.HelperCaching.cache_operator_output",
        mock_decorator_function,
    )
    with mock1, mock2, mock3, mock4:
        from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator

        op = LocalDcm2JsonOperator(dag="")
        op.airflow_workflow_dir = AIRFLOW_WORKFLOW_DIR
        op.operator_in_dir = OPERATOR_IN_DIR
        op.operator_out_dir = OPERATOR_OUT_DIR
        op.batch_name = BATCH_NAME

        op.manage_cache = "ignore"

        run_dir = Path(op.airflow_workflow_dir, dag.run_id)

        ct_path = run_dir / BATCH_NAME / "ct" / OPERATOR_IN_DIR / "ct.dcm"
        seg_path = run_dir / BATCH_NAME / "seg" / OPERATOR_IN_DIR / "seg.dcm"
        rtst_path = run_dir / BATCH_NAME / "rtst" / OPERATOR_IN_DIR / "rtst.dcm"

        generate_ct(ct_path, params)
        generate_seg(seg_path, params)
        generate_rtstruct(rtst_path, params)

        op.start()

        ct_path = run_dir / BATCH_NAME / "ct" / OPERATOR_OUT_DIR / "ct.json"
        seg_path = run_dir / BATCH_NAME / "seg" / OPERATOR_OUT_DIR / "seg.json"
        rtst_path = run_dir / BATCH_NAME / "rtst" / OPERATOR_OUT_DIR / "rtst.json"

        with open(ct_path, "r") as fp:
            json_ct = json.load(fp)
        with open(seg_path, "r") as fp:
            json_seg = json.load(fp)
        with open(rtst_path, "r") as fp:
            json_rtst = json.load(fp)
        return (json_ct, json_seg, json_rtst)


@pytest.mark.fixt_data(
    {
        "PatientName": 'SAIC_Pfenning_Prop++luss"2"^1.Messung2',
        "Manufacturer": 'ÜÖÄßÄ/*-+My üöä+M+SAIC_Pfenning_Propluss"2"^1.Messunga+nurer\\{\\}@',
        "InstitutionName": "My\\{Int\\}io+n-12345678900-==][]' @!@##$%^&*()_",
    },
)
def test_standard_ct(op):
    json_ct, _, _ = op

    assert (
        json_ct["00100010 PatientName_keyword_alphabetic"]
        == 'SAIC_Pfenning_Prop++luss"2"^1.Messung'
    )
