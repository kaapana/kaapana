from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, default_registry
from kaapana.blueprints.kaapana_global_variables import WORKFLOW_DIR, BATCH_NAME
from datetime import timedelta
import sys, os
import glob
import shutil
from subprocess import PIPE, run
import pydicom
from pathlib import Path
import requests
import time

class LocalDicomSendOperator(KaapanaPythonBaseOperator):
    def check_if_arrived(self, seriesUID):
        print("#")
        print("############### Check if DICOMs arrived ###############")
        print("#")
        max_tries = 30
        tries = 0
        while tries < max_tries:
            pacs_dcmweb_endpoint = f"http://{self.host}:8080/dcm4chee-arc/aets/KAAPANA/rs/instances"

            payload = {
                'SeriesInstanceUID': seriesUID
            }
            print("#")
            print(f"# request: {pacs_dcmweb_endpoint}: {payload}")
            print("#")
            httpResponse = requests.get(pacs_dcmweb_endpoint, params=payload, timeout=2)
            if httpResponse.status_code == 200:
                print("# Series found -> success !")
                break
            else:
                print("# Series not found -> sleep 2s !")
                tries += 1
                time.sleep(2)
        print("#")
        print("# Done")
        print("#")
        if tries >= max_tries:
            print("# -> too many failed requests -> Error!")
            print("# ABORT")
            return False
        else:
            return True

    def send_dicom_data(self, send_dir, series_uid):
        if not list(Path(send_dir).rglob('*.dcm')):
            print(send_dir)
            print("############### no dicoms found...!")
            raise FileNotFoundError
        print(f'Sending {send_dir} to {self.host} {self.port} with aetitle {self.aetitle} and aetitle_send {self.aetitle_send}')
        command = ['dcmsend', '-v', f'{self.host}', f'{self.port}', '-aet', f'{self.aetitle_send}', '-aec', f'{self.aetitle}', '--scan-directories',
                   '--recurse', f'{send_dir}']
        timeout = self.execution_timeout.seconds - 60
        print("The timeout is set to: ", timeout)
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
        if output.returncode != 0:
            print("############### Something went wrong with dcmsend!")
            for line in str(output).split("\\n"):
                print(line)
            print("##################################################")
            exit(1)
        if self.check_arrival and not self.check_if_arrived(seriesUID=series_uid):
            print(f"Arrival check failed!")
            exit(1)

    def start(self, **kwargs):
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        no_data_processed = True
        for batch_element_dir in batch_folders:
            print("input operator ", self.operator_in_dir)
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print(element_input_dir)

            dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "**/*.dcm*"), recursive=True))
            number_of_instances = len(dcm_files)
            if number_of_instances == 0:
                continue

            print("Number of instances to send: ", number_of_instances)
            dcm_file = dcm_files[0]
            print("dcm-file: {}".format(dcm_file))
            ds = pydicom.dcmread(dcm_file)
            series_uid = str(ds[0x0020, 0x000E].value)
            self.send_dicom_data(element_input_dir, series_uid)




    def __init__(self,
                 dag,
                 pacs_host='dcm4chee-service.store.svc',
                 pacs_port="11115",
                 ae_title="KAAPANA",
                 aetitle_send="kaapana",
                 check_arrival="False",
                 **kwargs):

        # The use of the local operator, to be able to set the aetitle_send!
        self.host = pacs_host
        self.port = pacs_port
        self.aetitle = ae_title
        self.aetitle_send = aetitle_send
        self.check_arrival = check_arrival
        self.name = "save_to_local_pacs"
        self.task_id = self.name
        


        super().__init__(
            dag=dag,
            task_id=self.task_id,
            name=self.name,
            python_callable=self.start,
            execution_timeout=timedelta(minutes=60),
            **kwargs)



