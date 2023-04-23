from kaapana.operators.KaapanaBaseOperator import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    KaapanaBaseOperator,
)
from datetime import timedelta


class GenerateThumbnailOperator(KaapanaBaseOperator):
    """
    TODO!
    """

    def __init__(self, dag, orig_image_operator, env_vars=None, **kwargs):
        """
        :param target_filename: Only for packing. The created file.
        TODO
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "ORIG_IMAGE_OPERATOR_DIR": str(orig_image_operator.operator_out_dir),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/seg-thumbnail-generator:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=timedelta(minutes=15),
            ram_mem_mb=4000,
            ram_mem_mb_lmt=8000,
            **kwargs,
        )
