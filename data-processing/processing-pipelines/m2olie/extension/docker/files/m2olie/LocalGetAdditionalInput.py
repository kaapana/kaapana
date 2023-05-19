import json
import os
import shutil
import time
import requests
from pathlib import Path
from typing import List, Dict
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_utils import get_release_name
from kaapana.blueprints.kaapana_global_variables import PROCESSING_WORKFLOW_DIR, ADMIN_NAMESPACE, SERVICES_NAMESPACE, JOBS_NAMESPACE
class LocalGetAdditionalInput(KaapanaPythonBaseOperator):

    def get_data(self, seriesUID):
        target_dir = os.path.join(
            self.airflow_workflow_dir,
            dag_run_id,
            self.batch_name,
            f"{seriesUID}",
            self.operator_out_dir,
        )

        download_successfull = HelperDcmWeb.downloadSeries(
            seriesUID=seriesUID, target_dir=target_dir
        )
        if not download_successfull:
            print("Could not download DICOM data!")
            download_successful = False
        return download_successfull


    def start(self, ds, **kwargs):
        workflow_from = kwargs['dag_run'].conf["data_form"]["workflow_form"]
        additional_identifiers = workflow_from["additional_identifiers"]
        print("Additional Identifiers: ", additional_identifiers)
        series_download_fail = []
        for series_uid in additional_identifiers:
            download_successfull = self.get_data(series_uid)
            if not download_successfull:
                    series_download_fail.append(series_uid)

            if len(series_download_fail) > 0:
                print("#####################################################")
                print("#")
                print(f"# Some series could not be downloaded! ")
                for series_uid in series_download_fail:
                    print("#")
                    print(f"# Series: {series_uid} failed !")
                    print("#")
                print("#####################################################")
                raise ValueError("ERROR")
    



    def __init__(self,
                 dag,
                 name='get_additional_input',
                 **kwargs):

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            **kwargs
        )