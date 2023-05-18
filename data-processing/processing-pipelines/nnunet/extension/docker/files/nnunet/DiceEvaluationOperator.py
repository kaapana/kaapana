from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class DiceEvaluationOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(hours=10)

    def __init__(
        self,
        dag,
        gt_operator,
        ensemble_operator=None,
        anonymize=True,
        parallel_processes=1,
        name="dice-evaluation",
        batch_name=None,
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        envs = {
            "GT_IN_DIR": str(gt_operator.operator_out_dir)
            if gt_operator is not None
            else str(None),
            "ENSEMBLE_IN_DIR": str(ensemble_operator.operator_out_dir)
            if ensemble_operator is not None
            else str(None),
            "ANONYMIZE": str(anonymize),
            "THREADS": str(parallel_processes),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/dice-evaluation:{KAAPANA_BUILD_VERSION}",
            name=name,
            batch_name=batch_name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=6200,
            ram_mem_mb_lmt=150000,
            **kwargs,
        )
