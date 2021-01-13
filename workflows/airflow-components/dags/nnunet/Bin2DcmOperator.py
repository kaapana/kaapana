import os
import pydicom
from datetime import timedelta
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project

class Bin2DcmOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=10)

    def __init__(self,
                 dag,
                 file_extensions="*.zip",
                 size_limit=100,
                 study_description="nnUnet model",
                 study_uid=pydicom.uid.generate_uid(),
                 name="bin2dcm",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):

        envs = {
            "EXTENSIONS": file_extensions,
            "SIZE_LIMIT_MB": str(size_limit),
            "STUDY_UID": str(study_uid),
            "STUDY_DESCRIPTION": str(study_description)
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/bin2dcm:3.6.4-vdev".format(default_registry, default_project),
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=5000,
            *args,
            **kwargs
        )
