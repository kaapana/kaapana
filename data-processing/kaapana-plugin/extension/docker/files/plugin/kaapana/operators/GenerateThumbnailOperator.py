from kaapana.operators.KaapanaBaseOperator import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    KaapanaBaseOperator,
)
from datetime import timedelta


class GenerateThumbnailOperator(KaapanaBaseOperator):
    def __init__(self, dag, get_ref_series_operator, env_vars=None, **kwargs):
        if env_vars is None:
            env_vars = {}

        envs = {
            "GET_REF_SERIES_OPERATOR_DIR": str(get_ref_series_operator.operator_out_dir),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/thumbnail-generator:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=timedelta(minutes=15),
            ram_mem_mb=4000,
            ram_mem_mb_lmt=8000,
            **kwargs,
        )
