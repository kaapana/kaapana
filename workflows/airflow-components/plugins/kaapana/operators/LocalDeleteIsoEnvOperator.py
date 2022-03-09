import os
import glob
import zipfile

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteIsoEnvOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        print("Delete isolated environment...")
        print(kwargs)

        # run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        # batch_input_dir = os.path.join(run_dir, self.operator_in_dir)
        # print('input_dir', batch_input_dir)

        # batch_output_dir = os.path.join(run_dir, self.operator_out_dir)  # , project_name)
        # if not os.path.exists(batch_output_dir):
        #     os.makedirs(batch_output_dir)

        # for file_path in glob.glob(os.path.join(batch_input_dir, '*.zip')):
        #     with zipfile.ZipFile(file_path, 'r') as zip_ref:
        #         zip_ref.extractall(batch_output_dir)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="delete-iso-env",
            python_callable=self.start,
            **kwargs
        )
