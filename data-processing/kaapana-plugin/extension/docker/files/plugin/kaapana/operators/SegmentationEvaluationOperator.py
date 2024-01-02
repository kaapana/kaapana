from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class SegmentationEvaluationOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        gt_operator,
        test_operator,
        batch_gt,
        batch_test,
        name="segmentation-evaluation",
        env_vars={},
        execution_timeout=timedelta(hours=12),
        **kwargs,
    ):
        envs = {
            "GT_IN_DIR": str(gt_operator.operator_out_dir),
            "TEST_IN_DIR": str(test_operator.operator_out_dir),
            "BATCH_GT": str(batch_gt),
            "BATCH_TEST": str(batch_test),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/seg-eval:{KAAPANA_BUILD_VERSION}",
            name=name,
            batch_name=batch_test,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=5000,
            ram_mem_mb_lmt=100000,
            **kwargs,
        )
