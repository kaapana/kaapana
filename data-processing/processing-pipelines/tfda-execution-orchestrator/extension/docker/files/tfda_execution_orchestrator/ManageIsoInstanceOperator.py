import os
import json
import logging
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from datetime import timedelta


class ManageIsoInstanceOperator(KaapanaBaseOperator):        
    execution_timeout = timedelta(hours=10)
    def load_config(self, config_filepath):
        with open(config_filepath, "r") as stream:
            try:
                config_dict = json.load(stream)
                return config_dict
            except Exception as exc:
                raise AirflowFailException(f"Could not extract configuration due to error: {exc}!!")
    
    def __init__(self,
                 dag,
                 instanceState = "present",
                 taskName = "create-iso-inst",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 **kwargs):
        
        name = taskName
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        platform_config_path = os.path.join(operator_dir, "platform_specific_config", "platform_config.json")
        platform_config = self.load_config(platform_config_path)        
        envs = {
            "INSTANCE_STATE": str(instanceState),
            "PLATFORM_CONFIG": str(platform_config)
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/trigger-ansible-playbook:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs
        )

