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
                 level='element',
                 execution_timeout=timedelta(minutes=20),
                 *args, **kwargs
                 ):

        if level not in ['element', 'pile']:
            raise NameError('level must be either "element" or "pile". \
                If pile, an operator folder next to the batch folder with .dcm files is expected. \
                If element, *.dcm are expected in the corresponding operator with .dcm files is expected.'
            )

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "HOST": str(pacs_host),
            "PORT": str(pacs_port),
            "AETITLE": str(ae_title),
            "LEVEL": str(level)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/dcmsend:3.6.4-vdev".format(default_registry, default_project),
            name="dcmsend",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            *args, **kwargs
            )