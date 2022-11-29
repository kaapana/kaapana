from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
from datetime import timedelta

class ExtractScanparameterOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=120),
                 **kwargs
                 ):

        super().__init__(
            dag=dag,
            image=f"{default_registry}/scanparam2json:{kaapana_build_version}",
            name='extract-scanparam',
            image_pull_secrets=['registry-secret'],
            execution_timeout=execution_timeout,
            **kwargs
        )