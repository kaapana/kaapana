import os
import glob
from datetime import timedelta


from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry

class PytorchExecuterBaseOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='pytorch-executor',
                 execution_timeout=timedelta(minutes=20),
                 *args, **kwargs
                 ):

        volume_mounts = [
            # VolumeMount('miniodata', mount_path='/minio', sub_path=None, read_only=False),
            VolumeMount('executablesdata', mount_path='/executables', sub_path=None, read_only=False)
            ]

        volumes = [
            # Volume(name='miniodata', configs={
            #     'hostPath':
            #     {
            #         'type': 'DirectoryOrCreate',
            #         'path': os.getenv('MINIODIR', "/home/kaapana/minio")
            #     }
            # }),
            Volume(name='executablesdata', configs={
                'hostPath':
                {
                    'type': 'DirectoryOrCreate',
                    'path': os.getenv('EXECUTABLESDIR', "/home/kaapana/workflows/executables")
                }
            })
        ]

        super().__init__(
            dag=dag,
            name=name,
            image=f"{default_registry}/pytorch-executer:0.1.0",
            image_pull_secrets=["registry-secret"],
            volume_mounts=volume_mounts,
            volumes=volumes,
            execution_timeout=execution_timeout,
            *args, **kwargs
        )