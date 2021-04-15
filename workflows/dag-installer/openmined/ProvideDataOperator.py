import os
import glob
import pydicom
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class OpenminedProvideDataOperator(KaapanaBaseOperator):

    @staticmethod
    def on_success(info_dict):
        print("##################################################### on_success!")
        pod_id = info_dict["ti"].task.kube_name
        print("--> training ended, now delete pod {} !".format(pod_id))
        KaapanaBaseOperator.pod_stopper.stop_pod_by_name(pod_id=pod_id)

    def execute(self, context):
        try:
            KaapanaBaseOperator.execute(self, context)
        except TypeError:
            pass
    
    def __init__(self,
                 dag,
                 hostname=None,
                 port=None,
                 lifespan=None,
                 dataset=None,
                 exp_tag=None,
                 env_vars=None,
                 execution_timeout=timedelta(hours=6),
                 *args, **kwargs
                 ): 

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "HOSTNAME": str(hostname),
            "PORT": str(port),
            "DATASET": str(dataset),
            "EXP_TAG": str(exp_tag),
            "LIFESPAN": str(lifespan)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="data-provider",
            image="{}{}/openmined-provide-data:0.1.0-vdev".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            on_success_callback=OpenminedProvideDataOperator.on_success,
            #image_pull_policy='Always',
            #ram_mem_mb=5000,
            *args, **kwargs
            )
