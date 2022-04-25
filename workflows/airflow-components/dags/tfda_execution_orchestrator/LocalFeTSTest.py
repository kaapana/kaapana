import os
import glob
import zipfile
from subprocess import PIPE, run

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalFeTSTest(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        return 'Hello Fets !!!!!!!!!!!!!!!!!!!!!!!!'

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="fets-test",
            python_callable=self.start,
            **kwargs
        )