import glob
import os
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperDcmWeb import HelperDcmWeb


class LocalDicomSendOperator(KaapanaPythonBaseOperator):
    """
    Operator sends data to the platform locally.

    This operator is used for sending data to the platform locally.
    """

    def start(self, **kwargs):
        self.conf = kwargs["dag_run"].conf
        self.dcmweb_helper = HelperDcmWeb(
            dag_run=kwargs["dag_run"]
        )
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folders = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]
        for batch_element_dir in batch_folders:
            print("input operator ", self.operator_in_dir)
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print(element_input_dir)

            dcm_files = sorted(
                glob.glob(os.path.join(element_input_dir, "**/*.dcm*"), recursive=True)
            )
            number_of_instances = len(dcm_files)
            if number_of_instances == 0:
                continue
            print("Number of instances to send: ", number_of_instances)
            self.dcmweb_helper.upload_dcm_files(element_input_dir)

    def __init__(
        self,
        dag,
        ae_title: str = "KAAPANA",
        **kwargs,
    ):
        """
        Constructor for the LocalDicomSendOperator.
        """

        self.aetitle = ae_title

        super().__init__(
            dag=dag,
            task_id="local-dcm-send",
            name="local-dcm-send",
            python_callable=self.start,
            execution_timeout=timedelta(minutes=60),
            **kwargs,
        )
