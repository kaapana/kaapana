
from minio import Minio
import os
import time
import glob
from datetime import timedelta
from datetime import datetime
import shutil
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import WORKFLOW_DIR

class LocalCleanUpExpiredWorkflowDataOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        
        print(f'Expired time {self.expired_period}')        
        print(f'Working in {WORKFLOW_DIR}')
        for dag_id in os.listdir(WORKFLOW_DIR):
            target_dir = os.path.join(WORKFLOW_DIR, dag_id)
            youngest_time = 0
            modified_time = 0
            for file_path in glob.glob(f'{target_dir}/**/*', recursive=True):
                modified_time = os.path.getmtime(file_path)
                if modified_time > youngest_time:
                    youngest_time = modified_time
            age_in_seconds = time.time() - youngest_time
            print(f'Checking in {dag_id}')
            print(f'Age of directory {timedelta(seconds=age_in_seconds)}')
            print(f'Last changed {datetime.fromtimestamp(modified_time).strftime("%A, %B %d, %Y %I:%M:%S")}')
            if age_in_seconds > self.expired_period.total_seconds():
                print(f'Removing folder since it was last modified on the {datetime.fromtimestamp(modified_time).strftime("%A, %B %d, %Y %I:%M:%S")}')
                shutil.rmtree(target_dir, ignore_errors=True)
        return

    def __init__(self,
        dag,
        expired_period=timedelta(days=60),
        **kwargs
        ):
        
        self.expired_period = expired_period
        
        super().__init__(
           dag=dag,
           name=f'clean-up',
           python_callable=self.start,
           **kwargs
        )