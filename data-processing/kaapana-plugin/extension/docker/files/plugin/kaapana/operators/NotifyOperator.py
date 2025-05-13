from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class NotifyOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="notify",
        topic=None,
        title=None,
        description=None,
        icon=None,
        link=None,
        execution_timeout=timedelta(seconds=30),
        env_vars=None,
        **kwargs,
    ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "TITLE": str(title),
            "TOPIC": str(topic),
            "DESCRIPTION": str(description),
            "ICON": str(icon),
            "LINK": str(link),
        }
        env_vars.update(envs)
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/notify:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs,
        )
