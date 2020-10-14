from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta


class OrganSegmentationOperator(KaapanaBaseOperator):

    execution_timeout = timedelta(minutes=30)

    def __init__(self,
                 dag,
                 mode,
                 threads=8,
                 env_vars=None,
                 spleen_operator=None,
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "MODE": str(mode),
            "OMP_NUM_THREADS": str(threads),
            "OMP_THREAD_LIMIT": str(threads),
            "SPLEEN_OPERATOR_DIR": spleen_operator.operator_out_dir if spleen_operator is not None else ''
        }

        env_vars.update(envs)

        if mode is not None and parallel_id is None:
            parallel_id = mode.lower().replace(" ", "-")

        super().__init__(
            dag=dag,
            image="{}{}/shape-organseg:0.1.1".format(default_registry, default_project),
            name="organ-segmentation",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            task_concurrency=10,
            ram_mem_mb=4000,
            *args, 
            **kwargs
            )
