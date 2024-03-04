from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class SegmentationEvaluationOperator(KaapanaBaseOperator):
    """
    This operator evaluates segmentation metrics by comparing two sets of segmentations: ground truth (gt) and predictions (test).
    It differentiates between these sets using a tag defined in the UI form under `test_tag_key`. 
    The evaluation process involves comparing binarized `combine_masks.nii.gz` files. 
    Users are responsible for filtering relevant classes before using this operator.

    Inputs:
        gt_operator (str): Identifier for the prior operator processing ground truth segmentations. Expects ground truth
                        segmentations in its output directory.
        test_operator (str): Identifier for the prior operator processing test (prediction) segmentations. Expects test 
                            segmentations in its output directory.
        batch_gt (str): Name of the batch folder for ground truth data. All prior processing of ground truth segmentations
                        should occur within this folder.
        batch_test (str): Name of the batch folder for test data. All prior processing of test segmentations should occur
                        within this folder.
        metrics_key (str, default='metrics'): Key within `ui_forms['workflow_form']['properties']` for specifying metrics to compute.
        test_seg_exists (bool, default=True): Only set to `False` only if the DAG runs `nnunet predict` before this operator (experimental).

    Outputs:
        dataset_map.json (file): JSON file mapping each test and ground truth data identifier to their respective file paths.
        metrics.json (file): JSON file containing calculated metrics, grouped by each test identifier.
    """

    def __init__(
        self,
        dag,
        gt_operator,
        test_operator,
        batch_gt,
        batch_test,
        metrics_key="metrics",
        test_seg_exists=True,
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
            "METRICS_KEY": str(metrics_key),
            "TEST_SEG_EXISTS": str(test_seg_exists),
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
            labels={"network-access": "opensearch"},
            **kwargs,
        )
