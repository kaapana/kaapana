from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from datetime import timedelta

class Itk2DcmOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name=None,
                 execution_timeout=timedelta(minutes=90),
                 *args, **kwargs
                 ) -> None:

        name = name if name is not None else "itk2dcm-converter"

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/itk2dcm:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )