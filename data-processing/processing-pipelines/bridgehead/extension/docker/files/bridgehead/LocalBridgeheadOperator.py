import subprocess
import os
import errno
import glob
import json
import shutil
import requests
import time
import zipfile

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalBridgeheadOperator(KaapanaPythonBaseOperator):
    """ """

    def generate_config(self, run_dir):
        auth_header = {"x-api-key": self.auth_key}
        temp_zip_file = os.path.join(run_dir, self.operator_out_dir, "tempzip.zip")
        return {
            "auth_header": auth_header,
            "base_url": self.base_url,
            "temp_zip_file": temp_zip_file,
        }

    def create_export_task(self, pseudonyms, config):
        # '&'.join(['identifier={}'.format(pseudonym)
        query_string = "Patient?identifier=" + ",".join(pseudonyms)
        payload = {
            "query": query_string,
            "query-format": "FHIR_SEARCH",
            "template-id": "ccp",
            "output-format": "CSV",
        }
        endpoint = f"{config['base_url']}/request"
        print(f"Payload: {payload}\nEndpoint: {endpoint}")

        r = requests.post(
            endpoint, data=payload, headers=config["auth_header"], verify=False
        )

        # Extract Query ID
        return_value = r.json()["responseUrl"].rsplit("=")
        if len(return_value) != 2:
            raise RuntimeError
        return return_value[1]

    def check_export_status(self, query_id, config):
        endpoint = f"{config['base_url']}/status?query-execution-id={query_id}"
        r = requests.get(endpoint, headers=config["auth_header"], verify=False)
        print("Export status: ", r.text)
        return_value = r.text
        return return_value == '"OK"'

    def get_results_zip(self, query_id, config):
        endpoint = f"{config['base_url']}/response?query-execution-id={query_id}"
        r = requests.get(
            endpoint, headers=config["auth_header"], stream=True, verify=False
        )
        with open(config["temp_zip_file"], "wb") as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)

    def start(self, ds, **kwargs):
        print("Starting module LocalBridgeheadOperator...")
        print(kwargs)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        config = self.generate_config(run_dir)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]
        pseudonyms = []
        for batch_element_dir in batch_dirs:
            metadata_json = glob.glob(
                os.path.join(batch_element_dir, self.operator_in_dir, "*.json*")
            )[
                0
            ]  # Take first (and only) JSON file

            with open(metadata_json, "r") as f:
                data = json.load(f)
                patient_id = data.get("00100020 PatientID_keyword")
                if patient_id:
                    print(f"PatientID: {patient_id}")
                    pseudonyms.append(patient_id)

        # 2. TODO: Get patient pseudonyms from OpenSearch/PACS
        pseudonyms = ["W7XHWHEP", "HR0FY61P", "8MNC7P16", "55Y7A6M0", "4AC3VWWW"]

        # 3. Send request to exporter (opt: generate template)
        query_id = self.create_export_task(pseudonyms, config)
        print("Export request filed under query ID:", query_id)

        # 4. Check status and download export
        while not self.check_export_status(query_id, config):
            time.sleep(10)  # Time is in seconds
        print("Fetching result zip")
        self.get_results_zip(query_id, config)

        # 5. TODO: Uncompress zip?

    def __init__(self, dag, **kwargs):
        # TODO: add base_url to envs and auth_key to e.g. an kubernetes-secret
        self.base_url = "add-here"
        self.auth_key = "CHANGEME"

        super().__init__(
            dag=dag, name="bridgehead", python_callable=self.start, **kwargs
        )
