import os
import sys
from pathlib import Path
from unittest.mock import patch

from attr import dataclass
import pytest
from tests.mock_modules import mock_modules
from tests.generator import generate_dcms
from airflow.models.skipmixin import SkipMixin
from airflow.operators.python import PythonOperator

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent
        / "../data-processing/kaapana-plugin/extension/docker/files/plugin/"
    ),
)

mock_modules()

from kaapana.operators.KaapanaPythonBaseOperator import (
    KaapanaPythonBaseOperator,
)


def __init__(self, *args, **kwargs):
    pass


@dataclass
class Dag:
    run_id: str


@pytest.fixture
def op():
    os.environ["DICT_PATH"] = (
        "services/flow/airflow/docker/files/scripts/dicom_tag_dict.json"
    )

    dag = Dag(run_id="test_run")

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
        from kaapana.operators.LocalDcm2JsonOperator import (
            LocalDcm2JsonOperator,
        )

        op = LocalDcm2JsonOperator(dag="", testing=True)
        op.operator_in_dir = "operator_in_dir"
        op.operator_out_dir = "operator_out_dir"
        op.manage_cache = "ignore"
        op.airflow_workflow_dir = "tests"
        op.batch_name = "batch_name"

        run_dir = Path(op.airflow_workflow_dir, dag.run_id)
        generate_dcms(run_dir, op.batch_name, op.operator_in_dir)
        return op


def test_exit_on_error_false(op):
    op.exit_on_error = False
    op.start()


def test_exit_on_error_true(op):
    op.exit_on_error = True
    with pytest.raises(Exception):
        op.start()
