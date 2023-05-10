from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta
import os


class GetZenodoModelOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=240)

    def __init__(
        self,
        dag,
        model_dir="/models/nnUNet",
        name="get-zenodo-models",
        task_ids=None,
        enable_proxy=True,
        delete_output_on_start=False,
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        envs = {"MODEL_DIR": str(model_dir), "LOG_LEVEL": "INFO"}
        env_vars.update(envs)

        if task_ids is not None:
            env_vars["TASK_IDS"] = task_ids

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/download-zenodo-models:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            enable_proxy=enable_proxy,
            delete_output_on_start=delete_output_on_start,
            ram_mem_mb=1000,
            **kwargs,
        )
