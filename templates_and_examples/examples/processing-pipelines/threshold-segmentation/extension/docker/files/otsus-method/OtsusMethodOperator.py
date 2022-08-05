from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_platform_abbr, default_platform_version


class OtsusMethodOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(seconds=30),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='otsus-method',
            image=f"{default_registry}/example-otsus-method:0.1.0", #{default_platform_abbr}_{default_platform_version}__0.1.0",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            operator_out_dir="otsus-method/",
            *args,
            **kwargs
        )