from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
from datetime import timedelta
import os


class GetTaskModelOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=240)

    def __init__(self,
                dag,
                name="get-task-model",
                task_id=None,
                zip_file=False,
                target_level="default",
                operator_out_dir="/models",
                mode="install_pretrained",
                enable_proxy=True,
                delete_output_on_start=False,
                env_vars={},
                execution_timeout=execution_timeout,
                **kwargs
                ):

        envs = {
            "MODE": str(mode),
            "TARGET_LEVEL": str(target_level),
            "ZIP_FILE": str(zip_file)
        }
        env_vars.update(envs)

        if task_id is not None:
            env_vars["TASK"] = task_id

        super().__init__(
            dag=dag,
            image=f"{default_registry}/nnunet-get-models:{kaapana_build_version}",
            name=name,
            operator_out_dir=operator_out_dir,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            enable_proxy=enable_proxy,
            delete_output_on_start=delete_output_on_start,
            ram_mem_mb=1000,
            **kwargs
        )
