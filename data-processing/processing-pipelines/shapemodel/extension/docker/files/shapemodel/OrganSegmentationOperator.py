from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class OrganSegmentationOperator(KaapanaBaseOperator):
    """
    Segments organs using a 3D Statistical Shape Model

    Paper: https://pubmed.ncbi.nlm.nih.gov/27541630/

    **Inputs:**

    * Data in NRRD format

    **Outputs:**

    * Segmentations in NRRD format
    """

    execution_timeout = timedelta(minutes=30)

    def __init__(
        self,
        dag,
        mode: str,
        threads=8,
        env_vars=None,
        spleen_operator=None,
        parallel_id=None,
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        """
        :param mode: Organ of interest. [unityCS, Liver, Spleen, RightKidney, LeftKidneyOnly]
        :param spleen_operator: Optional OrganSegmentationOperator with mode='spleen'
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "MODE": str(mode),
            "OMP_NUM_THREADS": str(threads),
            "OMP_THREAD_LIMIT": str(threads),
            "SPLEEN_OPERATOR_DIR": spleen_operator.operator_out_dir
            if spleen_operator is not None
            else "",
        }

        env_vars.update(envs)

        if mode is not None and parallel_id is None:
            parallel_id = mode.lower().replace(" ", "-")

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/shape-organseg:{KAAPANA_BUILD_VERSION}",
            name="organ-segmentation",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            max_active_tis_per_dag=25,
            ram_mem_mb=6000,
            **kwargs,
        )
