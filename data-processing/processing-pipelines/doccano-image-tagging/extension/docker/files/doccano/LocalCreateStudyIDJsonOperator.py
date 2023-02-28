
from minio import Minio
import os
import glob
import uuid
import json
import datetime
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_utils import generate_minio_credentials
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.HelperCaching import cache_operator_output

class LocalCreateStudyIDJsonOperator(KaapanaPythonBaseOperator):

    @cache_operator_output
    @rest_self_udpate
    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        if 'workflow_form' in conf and conf['workflow_form'] is not None and 'zip_files' in conf['workflow_form']:
                self.zip_files = conf['workflow_form']['zip_files']
                print('Zip files set by workflow_form', self.zip_files)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, '*'))]
        print(batch_folder)

        study_id_dict = {}
        for batch_element_dir in batch_folder:
            metadata_json = os.path.join(batch_element_dir, self.operator_in_dir, 'metadata.json')
            print(metadata_json)
            with open(metadata_json) as f:
                data = json.load(f)
                study_id = data["0020000D StudyInstanceUID_keyword"]
                if study_id in study_id_dict:
                    study_id_dict[study_id]["metadata"]["series_instance_uids"].append(data['0020000E SeriesInstanceUID_keyword'])
                else:
                    study_id_dict[study_id] = {
                        "text": f'study-id-{study_id}',
                        "metadata": {
                            "series_instance_uids": [data['0020000E SeriesInstanceUID_keyword']]
                        }
                    }
        to_be_uploaded = [v for k, v in study_id_dict.items()]
        print(to_be_uploaded)
        
        batch_output_dir = os.path.join(run_dir, self.operator_out_dir)
        if not os.path.exists(batch_output_dir):
            os.makedirs(batch_output_dir)
        
        with open(os.path.join(batch_output_dir, 'study_ids.json'), 'w') as f:
            json.dump(to_be_uploaded, f)

        return

    def __init__(self,
        dag,
        name='create-study-id-json',
        *args, **kwargs
        ):
    
        super().__init__(
           dag=dag,
           name=name,
           python_callable=self.start,
           execution_timeout=timedelta(minutes=30),
           *args,
           **kwargs
        )