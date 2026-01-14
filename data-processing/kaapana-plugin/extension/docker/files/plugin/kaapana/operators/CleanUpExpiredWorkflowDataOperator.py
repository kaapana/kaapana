from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)

class CleanUpExpiredWorkflowDataOperator(KaapanaBaseOperator):
    """
    Operator to cleanup/remove the expired workflows data directories

    **Inputs:**

    * expired_period: Clean items that have expired since a certain period.

    """
    def __init__(self, dag, expired_period=timedelta(days=60), env_vars=None, **kwargs):
        """
        :param dag: DAG in which the operator has to be executed.
        :param expired_period: Clean items that have expired since in day(s), default: 60 days
        """



        if env_vars is None:
            env_vars = {}

        envs = {
            "EXPIRED_PERIOD": str(int(expired_period.total_seconds())),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/cleanup-expired-workflows:{KAAPANA_BUILD_VERSION}",
            name="clean-up",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            **kwargs,
        )
