import datetime
import glob
import os
from datetime import timedelta
from zipfile import ZipFile

from persistence.HelperPersistence import CASClient
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import (
    KaapanaPythonBaseOperator,
    rest_self_udpate,
)


class LocalCASPutOperator(KaapanaPythonBaseOperator):
    """
    Operator to upload data into the Contend Adressable Storage component of the persistence layer
    """

    @cache_operator_output
    @rest_self_udpate
    def start(self, ds, **kwargs):
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folders = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]
        for batch_element_dir in batch_folders:
            print("input operator ", self.operator_in_dir)
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print(element_input_dir)
            files = sorted(
                glob.glob(os.path.join(element_input_dir, "**/*"), recursive=True)
            )
            number_of_files = len(files)
            if number_of_files == 0:
                continue
            print("Number of files to send: ", number_of_files)
            for f in files:
                print(self.cas.upload(f))

    def __init__(
        self,
        dag,
        name=None,
        action_operators=None,
        action_operator_dirs=None,
        action_files=None,
        cas_uri: str = f"http://kaapana-persistence-service.{SERVICES_NAMESPACE}.svc:8080/cas",
        **kwargs,
    ):
        """
        :param cas_uri: uri of the cas storeage
        """
        self.action_operator_dirs = action_operator_dirs or []
        self.action_operators = action_operators or []
        self.action_files = action_files or []

        self.cas = CASClient(cas_uri)
        name = name or "put-to-cas"
        super(LocalCASPutOperator, self).__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            execution_timeout=timedelta(minutes=30),
            **kwargs,
        )
