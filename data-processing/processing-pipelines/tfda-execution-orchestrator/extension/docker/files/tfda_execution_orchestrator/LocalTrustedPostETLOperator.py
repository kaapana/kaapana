import logging
from subprocess import PIPE, run
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalTrustedPostETLOperator(KaapanaPythonBaseOperator):

    def start(self, ds, ti, **kwargs):
        """TODO: Only a placeholder, will be filled soon"""
        logging.info("Process data after isolated execution...")

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="trusted-post-etl",
            python_callable=self.start,
            **kwargs
        )