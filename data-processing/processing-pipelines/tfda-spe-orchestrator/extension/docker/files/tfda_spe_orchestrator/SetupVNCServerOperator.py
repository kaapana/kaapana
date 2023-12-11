from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class SetupVNCServerOperator(KaapanaBaseOperator):
    """
    Operator to setup a VNC Server on a running Secure Processing Environment (SPE) instance.

    This operator extends the KaapanaBaseOperator and triggers a processing container that sets up
    a VNC server on an SPE instance. It is intended to be used within the Kaapana platform and makes use of
    specific Kaapana variables and configurations.

    Notes:
        1. Ensure that the environment variables such as the "TASK_TYPE" are passed.
    """

    execution_timeout = timedelta(hours=10)

    def __init__(
        self,
        dag,
        instanceState="present",
        taskName="setup-vnc-server",
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        name = taskName
        envs = {"INSTANCE_STATE": str(instanceState), "TASK_TYPE": name}
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/trigger-ansible-playbook:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs,
        )
