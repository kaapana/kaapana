import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from attr import dataclass
from mock_modules import mock_modules
from generator import generate_ct, generate_rtstruct, generate_seg
from airflow.models.skipmixin import SkipMixin
from airflow.operators.python import PythonOperator


mock_modules()

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent
        / "../data-processing/kaapana-plugin/extension/docker/files/plugin/"
    ),
)


from kaapana.operators.KaapanaPythonBaseOperator import (
    KaapanaPythonBaseOperator,
)


def __init__(self, *args, **kwargs):
    pass


@dataclass
class Dag:
    run_id: str


class LocalDcm2JsonOperatorTest(unittest.TestCase):

    def setUp(self):

        dag = Dag(run_id="TestID")

        def mock_decorator_function(func):
            def wrapper(*args, **kwargs):
                result = func(dag_run=dag, *args, **kwargs)
                return result

            return wrapper

        mock1 = patch.object(
            KaapanaPythonBaseOperator, "__init__", new=__init__
        )
        mock2 = patch.object(SkipMixin, "__init__", new=__init__)
        mock3 = patch.object(PythonOperator, "__init__", new=__init__)
        mock4 = patch(
            "kaapana.operators.HelperCaching.cache_operator_output",
            mock_decorator_function,
        )
        with mock1, mock2, mock3, mock4:
            from kaapana.operators.LocalDcm2JsonOperator import (
                LocalDcm2JsonOperator,
            )

            op = LocalDcm2JsonOperator(dag=DEFAULT_DAG_RUN_ID)
            op.operator_in_dir = "operator_in_dir"
            op.operator_out_dir = "operator_out_dir"
            op.manage_cache = "ignore"
            op.airflow_workflow_dir = "tests"
            op.batch_name = "batch_name"

            run_dir = Path(op.airflow_workflow_dir, dag.run_id)
            generate_ct(
                run_dir / op.batch_name / "batch1" / op.operator_in_dir, "ct"
            )
            generate_seg(
                run_dir / op.batch_name / "batch2" / op.operator_in_dir, "seg"
            )
            generate_rtstruct(
                run_dir / op.batch_name / "batch3" / op.operator_in_dir,
                "rtstruct",
            )
            op.exit_on_error = False
            op.start()
            os.environ["DICT_PATH"] = (
                "services/flow/airflow/docker/files/scripts/dicom_tag_dict.json"
            )

            self.op = LocalDcm2JsonOperator(dag="")

    def test_complete(self):
        self.op.start()


if __name__ == "__main__":
    unittest.main()
