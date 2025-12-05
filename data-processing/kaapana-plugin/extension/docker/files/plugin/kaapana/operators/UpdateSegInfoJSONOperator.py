from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class UpdateSegInfoJSONOperator(KaapanaBaseOperator):
    """
    UpdateSegInfoJSONOperator
    Operator to adapt the seginfo json file as per the labels available inside
    a multi-label mask.
    **Inputs:**
    * mode: "update_json" 

    **Outputs:**
    * adapted seg_info json file.

    """

    def __init__(
        self,
        dag,
        name="update-seginfo",
        mode="update_json",
        env_vars=None,
        execution_timeout=timedelta(minutes=60),
        ram_mem_mb=8000,
        gpu_mem_mb=None,
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}
        envs = {
            "MODE": str(mode),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/update-seginfo:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            enable_proxy=True,
            env_vars=env_vars,
            ram_mem_mb=ram_mem_mb,
            gpu_mem_mb=gpu_mem_mb,
            **kwargs,
        )
