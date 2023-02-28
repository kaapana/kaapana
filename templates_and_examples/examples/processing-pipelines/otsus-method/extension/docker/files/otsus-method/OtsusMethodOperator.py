from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


class OtsusMethodOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='otsus-method',
                 execution_timeout=timedelta(seconds=120),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name=name,
            image=f"{default_registry}/otsus-method:{kaapana_build_version}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            #operator_out_dir="otsus-method/",
            *args,
            **kwargs
        )