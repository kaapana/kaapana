import os
import glob
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry

class nnUNetFederatedOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='nnunet-federated',
                 execution_timeout=timedelta(days=5),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name=name,
            image=f"{default_registry}/nnunet-cpu:03-22",
            image_pull_secrets=["registry-secret"],
            cmds=["python3"],
            arguments=["-u", "/common/scripts/nnunet_federated/run_nnunet_federated.py"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            *args, **kwargs
        )