from datetime import timedelta


from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class TemplateExecBashOperator(KaapanaBaseOperator):
    def __init__(self, dag, execution_timeout=timedelta(minutes=15), *args, **kwargs):
        super().__init__(
            dag=dag,
            name="temp-exec-bash",
            image=f"{DEFAULT_REGISTRY}/bash-template:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs,
        )
