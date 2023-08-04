from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class BprOperator(KaapanaBaseOperator):
    """
    Regresses the body part a given slice is from.

    The Body Part Regression (BPR) operator translates the anatomy in a
    radiologic volume into a machine-interpretable form. Each axial slice maps
    to a slice score. The slice scores monotonously increase with patient
    height.

    Code: https://github.com/mic-dkfz/bodypartregression
    Paper: https://arxiv.org/abs/2110.09148

    **Inputs:**

    * Data in nifti format

    **Outputs:**

    * Regresses a slice score for each given sample

    """

    execution_timeout = timedelta(minutes=10)
    task_dict = {}

    def __init__(
        self,
        dag,
        stringify_json=False,
        env_vars={},
        parallel_id=None,
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        envs = {"STRINGIFY_JSON": str(stringify_json)}
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/bodypartregression:{KAAPANA_BUILD_VERSION}",
            name="bodypartregression",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            ram_mem_mb_lmt=6000,
            gpu_mem_mb=5000,
            env_vars=env_vars,
            **kwargs,
        )
