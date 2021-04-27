import os
from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
#from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
# --> TODO: on_success_back back owerwrite must be possible


class TrainingChestXrayOperator(KaapanaBaseOperator):

    @staticmethod
    def on_success(info_dict):
        print("##################################################### on_success!")
        pod_id = info_dict["ti"].task.kube_name
        print("--> training ended, now delete pod {} !".format(pod_id))
        KaapanaBaseOperator.pod_stopper.stop_pod_by_name(pod_id=pod_id)
    
    def __init__(self,
                 dag,
                 host_ip=None,
                 fed_round=None,
                 n_epochs=None,
                 batch_size=None,
                 use_cuda=None,
                 local_testing=None,
                 env_vars=None,
                 execution_timeout=timedelta(hours=1),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "HOST_IP": str(host_ip),
            "FED_ROUND": str(fed_round),
            "N_EPOCHS": str(n_epochs),
            "BATCH_SIZE": str(batch_size),
            'USE_CUDA': str(use_cuda),
            "LOCAL_TESTING": str(local_testing)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="model-training",
            image="{}{}/federated-exp-chest-xray-train:0.1.0-vdev".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            on_success_callback=TrainingChestXrayOperator.on_success,
            execution_timeout=execution_timeout,
            training_operator=True,
            enable_proxy=True,
            host_network=True,
            ram_mem_mb=4000,
            *args, **kwargs
            )