import os
import glob
import pydicom
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class OpenminedProvideDataOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 node_host=None,
                 node_port=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "NODE_HOST": str(node_host),
            "NODE_PORT": str(node_port)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="openmined-provide-data",
            image="{}{}/openmined-provide-data:0.1.0-vdev".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            *args, **kwargs
            )