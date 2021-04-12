import os
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class TrainingOperatorMNIST(KaapanaBaseOperator):

    @staticmethod
    def on_success(info_dict):
        print("##################################################### on_success!")
        pod_id = info_dict["ti"].task.kube_name
        print("--> training ended, now delete pod {} !".format(pod_id))
        KaapanaBaseOperator.pod_stopper.stop_pod_by_name(pod_id=pod_id)
    
    def __init__(self,
                 dag,
                 host_ip=None,
                 env_vars=None,
                 execution_timeout=timedelta(hours=6),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "HOST_IP": str(host_ip)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="model-training",
            image="{}{}/federated-training-mnist:0.1.0-vdev".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            on_success_callback=TrainingOperatorMNIST.on_success,
            execution_timeout=execution_timeout,
            training_operator=True,
            image_pull_policy='Always',
            ram_mem_mb=1000,
            *args, **kwargs
            )