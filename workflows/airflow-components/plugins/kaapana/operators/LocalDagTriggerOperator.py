import glob
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR, INITIAL_INPUT_DIR

class LocalDagTriggerOperator(KaapanaPythonBaseOperator):

    def copy(self, src, target):
        import shutil
        import errno
        print("src/dst:")
        print(src)
        print(target)

        try:
            shutil.copytree(src, target)
        except OSError as e:
            # If the error was caused because the source wasn't a directory
            if e.errno == errno.ENOTDIR:
                shutil.copy(src, target)
            else:
                print(('Directory not copied. Error: %s' % e))
                raise Exception('Directory not copied. Error: %s' % e)
                exit(1)

    def trigger_dag(self, ds, **kwargs):
        from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
        import uuid
        import time
        import os

        global es

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        dag_run_id = generate_run_id(self.trigger_dag_id)

        for batch_element_dir in batch_folder:
            src = os.path.join(batch_element_dir, self.operator_in_dir)
            target = os.path.join(WORKFLOW_DIR, dag_run_id, BATCH_NAME, os.path.basename(os.path.normpath(batch_element_dir)), INITIAL_INPUT_DIR)
            print(src, target)
            self.copy(src, target)

        trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, replace_microseconds=False)

    def __init__(self,
                 dag,
                 trigger_dag_id,
                 *args, **kwargs
                 ):

        self.trigger_dag_id = trigger_dag_id
        name = "trigger_" + self.trigger_dag_id

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.trigger_dag,
            *args, **kwargs
        )
