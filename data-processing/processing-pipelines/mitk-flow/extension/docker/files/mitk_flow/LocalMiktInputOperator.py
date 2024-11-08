import glob
import json
import os
from pathlib import Path

import pydicom
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalMiktInputOperator(KaapanaPythonBaseOperator):
    """
    Operator to create an "MITK Segmentation Task List".
    https://docs.mitk.org/2024.06/MITKSegmentationTaskListsPage.html

    """

    def __init__(
        self,
        dag,
        operator_out_dir="mitk-results",
        reference_in_dir="get-ref-series",
        segmentation_in_dir="branch-get-reference",
        **kwargs
    ):
        self.reference_in_dir = reference_in_dir
        self.segmentation_in_dir = segmentation_in_dir

        super().__init__(
            dag=dag,
            name="get-mitk-input",
            operator_out_dir=operator_out_dir,
            python_callable=self.create_task_list,
            **kwargs
        )

    def dump_task_list(self, run_dir: str, tasks: list):
        """
        Save the created task list to the run directory.

        Args:
            run_dir (str): The directory path of the workflow execution
            tasks (list): List of task objects to be dumped
        """

        tasklist = dict()
        tasklist["FileFormat"] = "MITK Segmentation Task List"
        tasklist["Version"] = 1
        tasklist["Name"] = "Kaapana Task List"
        tasklist["Tasks"] = tasks

        with open(
            os.path.join(run_dir, "tasklist.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(tasklist, f, ensure_ascii=False, indent=4)

    def create_task_list(self, ds, **kwargs):
        """
        Generate an MITK tasklist based on the provided workflow data.

        Args:
            ds: airflow specific dataset
            **kwargs: Additional keyword arguments for task creation
        """
        run_dir = (
            Path(self.airflow_workflow_dir) / kwargs["dag_run"].run_id / self.batch_name
        )
        batch_folders = run_dir.glob("*")

        print("Starting module MtikInputOperator")

        tasks = list()
        number = 0
        for batch_element_dir in batch_folders:
            print("batch_element_dir: ", batch_element_dir)
            path_dir = os.path.basename(batch_element_dir)
            print("operator_in_dir: ", self.operator_in_dir)
            dcm_files = sorted(
                Path(batch_element_dir).joinpath(self.operator_in_dir).glob("*.dcm*")
            )
            seg_files = []
            if not len(dcm_files) > 0:
                print("Segmentation and reference images are used as input.")
                dcm_files = sorted(
                    Path(batch_element_dir)
                    .joinpath(self.reference_in_dir)
                    .glob("*.dcm*")
                )
                seg_files = sorted(
                    Path(batch_element_dir)
                    .joinpath(self.segmentation_in_dir)
                    .glob("*.dcm*")
                )

            if len(dcm_files) > 0:
                task = dict()
                incoming_dcm = pydicom.dcmread(dcm_files[0])
                seriesUID = incoming_dcm.SeriesInstanceUID
                patientID = incoming_dcm.PatientID + " task " + str(number)
                number = number + 1
                if len(seg_files) > 0:
                    task["Image"] = str(
                        Path(path_dir) / self.reference_in_dir / dcm_files[0].name
                    )
                    task["Segmentation"] = str(
                        Path(path_dir) / self.segmentation_in_dir / seg_files[0].name
                    )
                # otherwise only open images without segmentation
                else:
                    print("No segementaion, create scene with image only")
                    task["Image"] = str(
                        Path(path_dir) / self.operator_in_dir / dcm_files[0].name
                    )
                task["Result"] = os.path.join(
                    path_dir, self.operator_out_dir, "result.dcm"
                )
                task["Name"] = patientID
                tasks.append(task)
                print("task successfully added:")
                print(task)
        self.dump_task_list(run_dir, tasks)
