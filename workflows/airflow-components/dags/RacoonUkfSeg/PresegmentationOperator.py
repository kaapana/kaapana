from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry
from kaapana.kubetools.resources import Resources as PodResources
class PresegmentationOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=10000),
                 *args, **kwargs
                 ):

        pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=None)
        super().__init__(
            dag=dag,
            name='pathonomical-segmentation',
            image=f"{default_registry}/nnunet-tuda-ukf:0.1.18",
            execution_timeout=execution_timeout,
            pod_resources=pod_resources,
            ram_mem_mb=None,
            ram_mem_mb_lmt=None,
            gpu_mem_mb=5000,
            image_pull_secrets=["registry-secret"],
            *args,
            **kwargs
        )