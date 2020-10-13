from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class PoolJsonsOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(seconds=30),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='pool-json',
            image='dktk-jip-registry.dkfz.de/tutorial/example-pool-jsons:1.0-dkfz-vdev',
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )
