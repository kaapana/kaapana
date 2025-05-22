#from kaapana.kubetools.resources import Resources as PodResources
from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)

class LiverSgmentationOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=20),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='liver-tumor-segmentation-mri',
            image=f"{DEFAULT_REGISTRY}/liver-tumor-segmentation:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=timedelta(days=5),
            #operator_out_dir="liver-segmentation/",
            #ram_mem_mb=4000,
            ram_mem_mb_lmt=45000,
            #pod_resources=PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=None),
            *args,
            **kwargs
        )
