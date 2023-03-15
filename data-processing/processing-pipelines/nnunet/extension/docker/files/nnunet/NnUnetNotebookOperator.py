import os
import glob
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION

class NnUnetNotebookOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='nnunet-notebook-operator',
                 execution_timeout=timedelta(minutes=20),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/nnunet-gpu:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            cmds=["/bin/bash"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            *args, **kwargs
        )