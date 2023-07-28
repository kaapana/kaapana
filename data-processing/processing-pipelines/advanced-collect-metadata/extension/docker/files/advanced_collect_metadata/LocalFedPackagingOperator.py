import glob
import os
import json
import logging
import shutil
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME
from kaapana.blueprints.kaapana_utils import get_operator_properties
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperFederated import federated_sharing_decorator


class LocalFedPackagingOperator(KaapanaPythonBaseOperator):
    @federated_sharing_decorator
    @cache_operator_output
    def start(self, ds, **kwargs):
        run_id, dag_run_dir, dag_run, downstream_tasks = get_operator_properties(
            self.airflow_workflow_dir, **kwargs
        )

        if self.level == "batch":
            batch_folder = [f for f in glob.glob(dag_run_dir)]
        elif self.level == "element":
            batch_folder = [
                f for f in glob.glob(os.path.join(dag_run_dir, BATCH_NAME, "*"))
            ]
        else:
            print("No valid level expression given: either 'batch' or 'element' !")
        print(f"{batch_folder=}")

        for batch_element_dir in batch_folder:
            source = os.path.join(batch_element_dir, self.operator_in_dir)
            target = os.path.join(batch_element_dir, self.operator_out_dir)

            print(f"Copy {source} to {target}")
            shutil.copytree(source, target)

    def __init__(self, dag, level: str = "batch", **kwargs):
        self.level = level  # either "batch" or "element"

        super(LocalFedPackagingOperator, self).__init__(
            dag=dag,
            name=f"fed-packaging-operator",
            python_callable=self.start,
            allow_federated_learning=True,
            execution_timeout=timedelta(minutes=30),
            **kwargs,
        )
