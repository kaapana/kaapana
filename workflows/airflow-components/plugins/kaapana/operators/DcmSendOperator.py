import os
import glob
from datetime import timedelta
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class DcmSendOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 ae_title='KAAPANA',
                 pacs_host= 'ctp-service.flow.svc',
                 pacs_port='11112',
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "HOST": str(pacs_host),
            "PORT": str(pacs_port),
            "AETITLE": str(ae_title),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/dcmsend:3.6.2".format(default_registry, default_project),
            name="dcmsend",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            *args, **kwargs
            )