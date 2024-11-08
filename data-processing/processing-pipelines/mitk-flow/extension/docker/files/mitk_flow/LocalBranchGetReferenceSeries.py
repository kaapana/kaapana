import glob
import os
import shutil
from pathlib import Path

import pydicom
from kaapana.operators.KaapanaBranchPythonBaseOperator import (
    KaapanaBranchPythonBaseOperator,
)


class LocalBranchGetReferenceSeries(KaapanaBranchPythonBaseOperator):
    """
    Operator to branch incoming data:
    - For segmentations the reference image has to be downloaded
    - For images no additional data is needed

    """

    def branch_if_seg(self, ds, **kwargs):
        """
        Branch depending on input image:
        - Segmentations -> reference image is needed
        - Images -> use dirctly in the next opeator

        Args:
            run_dir (str): The directory path of the workflow execution
            tasks (list): List of task objects to be dumped
        """
        batch_folders = (
            Path(self.airflow_workflow_dir) / kwargs["dag_run"].run_id / self.batch_name
        ).glob("*")
        input_is_segmentation = False
        for batch_element_dir in batch_folders:
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print("Processing directory:", element_input_dir)
            dcm_file = next(
                iter(
                    glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True)
                ),
                None,
            )
            assert dcm_file
            ds = pydicom.dcmread(dcm_file)
            if ds.Modality == "SEG":
                assert "ReferencedSeriesSequence" in ds
                dst = os.path.join(batch_element_dir, self.operator_out_dir)
                print("Moving files from input dir: ", element_input_dir)
                print("dst: ", dst)
                shutil.move(element_input_dir, dst)
                input_is_segmentation = True

        if input_is_segmentation:
            return self.branch_to_ref_operator
        else:
            return self.branch_to_next_operator

    def __init__(
        self,
        dag,
        branch_to_ref_operator="get-ref-series",
        branch_to_next_operator="get-mitk-input",
        **kwargs
    ):
        self.branch_to_ref_operator = branch_to_ref_operator
        self.branch_to_next_operator = branch_to_next_operator
        super().__init__(
            dag=dag,
            name="branch-get-reference",
            python_callable=self.branch_if_seg,
            **kwargs
        )
