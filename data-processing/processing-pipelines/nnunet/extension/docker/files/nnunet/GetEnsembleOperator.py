from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os


class GetEnsembleOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=240)

    def __init__(self,
                 dag,
                 name="get-ensemble",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 **kwargs
                 ):

        # envs = {
        #     "MODE": str(mode),
        #     "TARGET_LEVEL": str(target_level),
        #     "ZIP_FILE": str(zip_file)
        # }
        # env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/nnunet-get-models:0.1.1",
            name=name,
            operator_out_dir="ensembel-model",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs
        )
