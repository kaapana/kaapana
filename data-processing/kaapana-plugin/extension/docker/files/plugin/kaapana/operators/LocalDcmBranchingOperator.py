import glob
import os
import shutil
from pathlib import Path
import pydicom
from typing import Callable, List
from kaapana.operators.KaapanaBranchPythonBaseOperator import (
    KaapanaBranchPythonBaseOperator,
)


class LocalDcmBranchingOperator(KaapanaBranchPythonBaseOperator):
    """
    Generic branching operator for Kaapana that applies a condition to DICOM files.
    Based on the condition, files are routed to different processing paths.

    Args:
        dag: The DAG instance to which this operator belongs.
        condition: A callable that takes a DICOM dataset (pydicom.FileDataset) as input
                   and returns True or False based on the condition.
        branch_true_operator: The task_id of the operator to branch to if the condition is True.
        branch_false_operator: The task_id of the operator to branch to if the condition is False.
        **kwargs: Additional keyword arguments for the operator.
    """

    def __init__(
        self,
        dag,
        condition: Callable[[pydicom.FileDataset], bool],
        branch_true_operator: str,
        branch_false_operator: str,
        **kwargs,
    ):
        self.condition = condition
        self.branch_true_operator = branch_true_operator
        self.branch_false_operator = branch_false_operator

        super().__init__(
            dag=dag,
            name="branch-on-condition",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )

    def start(self, ds, **kwargs):
        """
        Applies the condition to DICOM files in the batch and determines the branching path.

        Returns:
            str: The task_id of the operator to branch to based on the condition.
        """
        batch_folders = (
            Path(self.airflow_workflow_dir) / kwargs["dag_run"].run_id / self.batch_name
        ).glob("*")

        condition_met = False

        for batch_element_dir in batch_folders:
            dcm_files: List[Path] = sorted(
                list(
                    (batch_element_dir / self.operator_in_dir).rglob(
                        f"*.dcm"
                    )
                )
            )
            for dcm_file in dcm_files:
                ds = pydicom.dcmread(dcm_file)
                if self.condition(ds):
                    dst = os.path.join(batch_element_dir, self.operator_out_dir)

                    shutil.copy(dcm_file, dst)
                    condition_met = True

        if condition_met:
            return self.branch_true_operator
        return self.branch_false_operator
