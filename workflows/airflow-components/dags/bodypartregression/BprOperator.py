from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os
import json


class BprOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(days=5)
    task_dict = {}

    def __init__(self,
                 dag,
                 env_vars={},
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):
        envs = {

        }
        env_vars.update(envs)

        pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=None)
        training_operator = True
        gpu_mem_mb = 2000

        super().__init__(
            dag=dag,
            image="{}{}/bodypartregression:test".format(default_registry, default_project),
            name="bodypartregression",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=None,
            ram_mem_mb_lmt=None,
            pod_resources=pod_resources,
            training_operator=training_operator,
            gpu_mem_mb=gpu_mem_mb,
            env_vars=env_vars,
            *args,
            **kwargs
        )
