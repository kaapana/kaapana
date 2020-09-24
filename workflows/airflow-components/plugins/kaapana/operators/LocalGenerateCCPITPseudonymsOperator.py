import os
import glob
import json
import datetime
import requests
import pandas as pd
import requests
from io import StringIO

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

# Not tested


class LocalGenerateCCPITPseudonymsOperator(KaapanaPythonBaseOperator):

    def generate_pseudonym(self, dcm_data):

        endpoint_url = "http://dktk-bridge-dev:8180/ID-Manager/paths/getId"

        headers = {
            "apiKey": "test1234",
            "Content-Type": "application/json"
        }

        birth_date = dcm_data["00100030 PatientBirthDate_date"].split("-")
        year = birth_date[0]
        month = birth_date[1]
        day = birth_date[2]

        # TODO: Adapt data_fields
        idat_data = {
            "Vorname":  'Max',  # dcm_data["00100010 PatientName_keyword_alphabetic"],
            "Nachname":  'Mustermann',
            "Fruehere_Namen": 'Merlin',  # dcm_data["00100010 PatientName_keyword_alphabetic"],
            "Geburtstag": day,
            "Geburtsmonat": month,
            "Geburtsjahr":  year,
            "Staatsangehoerigkeit": "Deutsch",
            "Geschlecht":  dcm_data["00100040 PatientSex_keyword"],
            "idTypes": "JIP_HEIDELBERG_L-ID JIP_HEIDELBERG_G-ID",  # one or two possible
            "consented": "true"  # true or false possible
        }

        print(idat_data)

        r = requests.post(endpoint_url, headers=headers, json=idat_data)
        print(r.status_code)
        print(r.text)
        print(r.json)
        print('succesfull')
        resp_json = json.loads(r.json()["ids"])

        dcm_data['JIP_HEIDELBERG_L-ID'] = resp_json[0]["idString"]

        if len(resp_json) > 1:
            dcm_data['JIP_HEIDELBERG_G-ID'] = resp_json[1]["idString"]

        return dcm_data

    def start(self, ds, **kwargs):
        print("Starting moule LocalNLPDownloadProjectOperator...")
        print(kwargs)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        conf = kwargs['dag_run'].conf

        for batch_element_dir in batch_folder:

            target_dir = os.path.join(batch_element_dir, self.operator_out_dir)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            json_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print(("Pushing json files from: %s" % json_dir))
            json_list = glob.glob(json_dir+'/**/*.json', recursive=True)
            for j_file in json_list:
                with open(j_file) as f:
                    dcm_data = json.load(f)

                json_dict = self.generate_pseudonym(dcm_data)

                json_file_path = os.path.join(target_dir, "{}.json".format(os.path.basename(batch_element_dir)))

                with open(json_file_path, "w", encoding='utf-8') as jsonData:
                    json.dump(json_dict, jsonData, indent=4, sort_keys=True, ensure_ascii=True)

    def __init__(self,
                 dag,
                 *args, **kwargs):

        super().__init__(
            dag,
            name="gen-cppit-pseudonyms",
            python_callable=self.start,
            *args, **kwargs
        )
