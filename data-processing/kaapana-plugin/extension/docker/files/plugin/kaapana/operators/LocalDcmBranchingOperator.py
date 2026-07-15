# !!! DEPRECATION WARNING: Local Operators are deprecated and will be replaced with operators that run in Kubernetes pods in the next release v0.7.0.
# If you have a custom Local Operator, it should be migrated to a processing container based operator.
import glob
import os
import shutil
from pathlib import Path
from typing import Callable, List

import pydicom
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
        name: str = "branch-on-condition",
        **kwargs,
    ):
        self.condition = condition
        self.branch_true_operator = branch_true_operator
        self.branch_false_operator = branch_false_operator

        super().__init__(
            dag=dag,
            name=name,
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
        batch_root = (
            Path(self.airflow_workflow_dir) / kwargs["dag_run"].run_id / self.batch_name
        )
        batch_folders = batch_root.glob("*")

        none_satisfies_condition = True
        checked_files = 0
        readable_dicoms = 0
        matched_files = 0

        self.log.info("Checking DICOM branch condition in %s", batch_root)

        for batch_element_dir in batch_folders:
            input_dir = batch_element_dir / self.operator_in_dir
            dcm_files: List[Path] = sorted(list(input_dir.rglob("*.dcm")))

            if not dcm_files:
                dcm_files = sorted([p for p in input_dir.rglob("*") if p.is_file()])

            self.log.debug("Found %d candidate files in %s", len(dcm_files), input_dir)

            for dcm_file in dcm_files:
                checked_files += 1

                try:
                    dicom_ds = pydicom.dcmread(dcm_file, stop_before_pixels=True)
                except Exception:
                    self.log.debug("Skipping unreadable/non-DICOM file: %s", dcm_file)
                    continue

                readable_dicoms += 1

                if self.condition(dicom_ds):
                    out_dir = batch_element_dir / self.operator_out_dir
                    out_dir.mkdir(exist_ok=True, parents=True)
                    dst = out_dir / dcm_file.name
                    shutil.copy(dcm_file, dst)

                    matched_files += 1
                    none_satisfies_condition = False

        self.log.info(
            "Branch condition check finished: checked=%d readable_dicoms=%d matched=%d",
            checked_files,
            readable_dicoms,
            matched_files,
        )

        if none_satisfies_condition:
            self.log.info("Branching to %s", self.branch_false_operator)
            return self.branch_false_operator

        self.log.info("Branching to %s", self.branch_true_operator)
        return self.branch_true_operator
