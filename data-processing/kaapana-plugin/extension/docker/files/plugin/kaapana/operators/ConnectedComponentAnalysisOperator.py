from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class ConnectedComponentAnalysisOperator(KaapanaBaseOperator):
    """
    This operator takes a Nifti SEG and computes a connected component analysis (CCA).
    3D CCA is copmuted with the connected-component-3d package.

    **Inputs:**
    * Nifti SEG mask
    * 3D connectivity connectivity (6, 18, 26)

    **Outputs:**
    * CCA info w/ number of CC and number of voxels per CC
    """

    def __init__(
        self,
        dag,
        env_vars=None,
        json_operator=None,
        connectivity=26,
        execution_timeout=timedelta(days=5),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "JSON_INFO_DIR": str(json_operator.operator_out_dir)
            if json_operator is not None
            else str(None),
            "CONNECTIVITY": str(connectivity)
            if connectivity is not None
            else str(None),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/cca:{KAAPANA_BUILD_VERSION}",
            name="cca",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=5000,
            **kwargs,
        )
