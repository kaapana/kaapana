import glob
import os
import time
from datetime import timedelta
from pathlib import Path
from subprocess import PIPE, run

import pydicom
import requests
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperDcmWeb import HelperDcmWeb


class LocalDicomSendOperator(KaapanaPythonBaseOperator):
    """
    Operator sends data to the platform locally.

    This operator is used for sending data to the platform locally.
    For dcmsend documentation please have a look at https://support.dcmtk.org/docs/dcmsend.html.
    """

    def send_dicom_data(self, send_dir, series_uid):
        if len(list(Path(send_dir).rglob("*.dcm"))) == 0:
            print(send_dir)
            print("############### no dicoms found...!")
            raise FileNotFoundError
        print(
            f"Sending {send_dir} to {self.host} {self.port} with aetitle {self.aetitle} and aetitle_send {self.aetitle_send}"
        )
        command = [
            "dcmsend",
            "-v",
            f"{self.host}",
            f"{self.port}",
            "-aet",
            f"{self.aetitle_send}",
            "-aec",
            f"{self.aetitle}",
            "--scan-directories",
            "--scan-pattern",
            "*.dcm",
            "--recurse",
            f"{send_dir}",
        ]
        timeout = self.execution_timeout.seconds - 60
        print("The timeout is set to: ", timeout)
        output = run(
            command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout
        )
        if output.returncode != 0 or "with status SUCCESS" not in str(output):
            print("############### Something went wrong with dcmsend!")
            for line in str(output).split("\\n"):
                print(line)
            print("##################################################")
            raise ValueError("ERROR")
        else:
            print(f"Success! output: {output}")
            print("")
        if self.check_arrival and not self.dcmweb_helper.check_if_series_in_archive(
            seriesUID=series_uid
        ):
            print(f"Arrival check failed!")
            raise ValueError("ERROR")

    def start(self, **kwargs):
        self.conf = kwargs["dag_run"].conf
        self.dcmweb_helper = HelperDcmWeb(
            application_entity=self.aetitle, dag_run=kwargs["dag_run"]
        )
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folders = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]
        study_instance_uids = set()
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
            dcm_file = dcm_files[0]
            print("dcm-file: {}".format(dcm_file))
            ds = pydicom.dcmread(dcm_file)
            series_uid = str(ds[0x0020, 0x000E].value)
            self.send_dicom_data(element_input_dir, series_uid)
            study_instance_uids.add(str(ds[0x0020, 0x000D].value))

        for study_instance_uid in study_instance_uids:
            self.dcmweb_helper.set_access_control_id_of_study(study_instance_uid)
            self.dcmweb_helper.add_access_control_id_to_ae(study_instance_uid)

    def __init__(
        self,
        dag,
        pacs_host: str = f"dcm4chee-service.{SERVICES_NAMESPACE}.svc",
        pacs_port: str = "11115",
        ae_title: str = "KAAPANA",
        aetitle_send: str = "kaapana",
        check_arrival: str = "False",
        **kwargs,
    ):
        """
        :param pacs_host: Host of PACS
        :param pacs_port: Port of PACS
        :param ae_title: calling Application Entity (AE) title
        :param aetitle_send: called AE title of peer
        :param check_arrival: Verifies if data transfer was successful
        """

        # The use of the local operator, to be able to set the aetitle_send!
        self.host = pacs_host
        self.port = pacs_port
        self.aetitle = ae_title
        self.aetitle_send = aetitle_send
        self.check_arrival = check_arrival
        self.name = "local-dcm-send"
        self.task_id = self.name

        super().__init__(
            dag=dag,
            task_id=self.task_id,
            name=self.name,
            python_callable=self.start,
            execution_timeout=timedelta(minutes=60),
            **kwargs,
        )
