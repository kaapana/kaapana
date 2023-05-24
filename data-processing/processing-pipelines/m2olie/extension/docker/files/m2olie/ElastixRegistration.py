from datetime import timedelta, datetime

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class ElastixRegistration(KaapanaBaseOperator):
    """
    Registration Operator

    """

    def __init__(
        self,
        dag,
        operator_in_dir_fixed: str,
        operator_in_dir_moving: str,
        env_vars=None,
        name: str = "registration",
        execution_timeout: datetime = timedelta(minutes=60),
        **kwargs,
    ):
        """
        :param operator_in_dir_fixed: calling Application Entity (AE) title
        :param operator_in_dir_moving: Host of PACS
        """
        if env_vars is None:
            env_vars = {}

        envs = {
            "OPERATOR_IN_DIR_FIXED": operator_in_dir_fixed,
            "OPERATOR_IN_DIR_MOVING": operator_in_dir_moving,
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/m2olie-elastix-registration:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            # dev_server="code-server",
            **kwargs,
        )
