import os
import glob
import zipfile

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalRunAlgoSendResultOperator(KaapanaPythonBaseOperator):

    def start(self, ds, ti, **kwargs):
        print("Run algorithm in isolated environment and send result to source...")

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="run-algo",
            python_callable=self.start,
            **kwargs
        )
