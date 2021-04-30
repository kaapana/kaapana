from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta

class ExtractScanparameterOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=120),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            image="{}{}/scanparam2json:0.1.0-vdev".format(default_registry, default_project),
            name='extract-scanparam',
            image_pull_policy="Always",
            image_pull_secrets=['registry-secret'],
            execution_timeout=execution_timeout,
            *args, **kwargs
        )