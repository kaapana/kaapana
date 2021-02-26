import os
import shutil
import glob

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalWorkflowCleanerOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id) if self.run_dir is None else self.run_dir
        if self.clean_workflow_dir is True and (os.path.exists(run_dir)):
            print(("Cleaning dir: %s" % run_dir))
            shutil.rmtree(run_dir)

    def __init__(self,
                 dag,
                 clean_workflow_dir=True,
                 *args, **kwargs):

        self.clean_workflow_dir = clean_workflow_dir

        super().__init__(
            dag,
            name="workflow-cleaner",
            python_callable=self.start,
            *args, **kwargs
        )
