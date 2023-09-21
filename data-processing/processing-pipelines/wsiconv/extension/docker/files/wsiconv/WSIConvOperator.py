from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class WSIconvOperator(KaapanaBaseOperator):
    def __init__(
        self, dag, name=None, execution_timeout=timedelta(minutes=90), *args, **kwargs
    ) -> None:
        name = name if name is not None else "PixelMed-converter"

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/wsiconv:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=6000,
            ram_mem_mb_lmt=12000,
            #cmds=["tail"], 
            #arguments=["-f", "/dev/null"],
            *args,
            **kwargs,
        )
