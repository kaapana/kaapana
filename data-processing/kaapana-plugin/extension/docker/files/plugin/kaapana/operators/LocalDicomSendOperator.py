import os
from datetime import timedelta
from pathlib import Path

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb


class LocalDicomSendOperator(KaapanaPythonBaseOperator):
    """
    Operator sends data to the platform locally.

    This operator is used for sending data to the platform locally.
    """

    def __init__(self, dag, **kwargs):
        """
        Constructor for the LocalDicomSendOperator.
        """
        super().__init__(
            dag=dag,
            task_id="local-dcm-send",
            name="local-dcm-send",
            python_callable=self.start,
            execution_timeout=timedelta(minutes=60),
            **kwargs,
        )

    def start(self, **kwargs):
        self.dcmweb_helper = HelperDcmWeb()

        run_dir = (
            Path(self.airflow_workflow_dir) / kwargs["dag_run"].run_id / self.batch_name
        )
        # Creates a generator object of all the folders in the run directory
        batch_folders = run_dir.glob("*")

        for batch_element_dir in batch_folders:
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print("Processing directory:", element_input_dir)

            # upload_dcm_files does a walk through the directory and uploads all the dcm files
            self.dcmweb_helper.upload_dcm_files(element_input_dir)
