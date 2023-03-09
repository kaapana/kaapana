from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


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
            image=f"{DEFAULT_REGISTRY}/otsus-method:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            #operator_out_dir="otsus-method/",
            *args,
            **kwargs
        )