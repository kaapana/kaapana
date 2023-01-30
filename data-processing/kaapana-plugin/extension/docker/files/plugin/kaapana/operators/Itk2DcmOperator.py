from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
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
            image=f"{default_registry}/itk2dcm:{kaapana_build_version}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )