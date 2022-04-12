import os
import glob
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry

class TrainTestSplitOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='train-test-split',
                 execution_timeout=timedelta(minutes=20),
                 env_vars=None,
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        envs = {
            "HOSTDOMAIN": os.getenv('HOSTDOMAIN'),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"{default_registry}/pytorch-cpu-executer:0.1.0",
            image_pull_secrets=["registry-secret"],
            cmds=["python3"],
            arguments=["-u", "/common/scripts/train_test_split/run_train_test_split.py"], 
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            *args, **kwargs
        )