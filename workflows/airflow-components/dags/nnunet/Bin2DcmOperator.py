from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os


class Bin2DcmOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=10)

    def __init__(self,
                 dag,
                 file_extensions="*.zip",
                 size_limit=0,
                 study_description="nnUnet model",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):

        envs = {
            "EXTENSIONS": file_extensions,
            "SIZE_LIMIT_MB": str(size_limit),
            "STUDY_DESCRIPTION": str(study_description)
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/bin2dcm:3.6.2-vdev".format(default_registry, default_project),
            name="bin2dcm",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=5000,
            *args,
            **kwargs
        )
