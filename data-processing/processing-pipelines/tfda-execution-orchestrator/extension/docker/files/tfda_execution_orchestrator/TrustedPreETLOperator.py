import os
import logging
import requests
import subprocess
from subprocess import PIPE
from pathlib import Path
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from datetime import timedelta


class TrustedPreETLOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(hours=10)

    def __init__(self,
                 dag,
                 name = "trusted-pre-etl",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 **kwargs):
        
        envs = {

        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/pre-and-post-etl:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs
        )
