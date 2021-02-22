import os
import glob
from datetime import timedelta
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class OpenminedTrainModelOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 dataset=None,
                 grid_host=None,
                 grid_port=None,
                 epochs=None,
                 batch_size=None,
                 learning_rate=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "DATASET": str(dataset),
            "GRID_HOST": str(grid_host),
            "GRID_PORT": str(grid_port),
            "EPOCHS": str(epochs),
            "BATCH_SIZE": str(batch_size),
            "LEARNING_RATE": str(learning_rate)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="openmined-train-model",
            image="{}{}/openmined-train-model:0.1.0-vdev".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            #image_pull_policy='Always',
            *args, **kwargs
            )