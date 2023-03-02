import os
import glob
from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class FedartedSetupCentralTestOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='federated-setup-central-test',
                 execution_timeout=timedelta(minutes=20),
                 env_vars={},
                 *args, **kwargs
                 ):
        envs = {
            "SERVICES_NAMESPACE": os.getenv("SERVICES_NAMESPACE", None),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/federated-setup-central-test:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            env_vars=env_vars,
            *args, **kwargs
        )