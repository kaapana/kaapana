import os
from pathlib import Path

import pydicom
import requests

from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR, SERVICES_NAMESPACE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalPutToBackendOperator(KaapanaPythonBaseOperator):
    """
	This operater creates an entry in the backend for a given series.
    """

    def start(self, ds, **kwargs):
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        dcm_files = [*Path(run_dir, BATCH_NAME).rglob('*.dcm')]

        for dcm_file in dcm_files:
            print(
                f'Creating database entry for  {str(dcm_file)} in backend.'
            )
            try:
                series_instance_uid = pydicom.dcmread(dcm_file)[0x0020, 0x000e].value
                requests.post(
                    f'http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/client/identifier',
                    json={"identifier": series_instance_uid}
                )
            except Exception as e:
                print(f'Processing of {dcm_file} threw an error.', e)
                exit(1)

    def __init__(self,
                 dag,
                 name='put2backend',
                 **kwargs):

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            **kwargs
        )
