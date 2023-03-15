from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION

from airflow.utils.trigger_rule import TriggerRule


class TrainValDataSplitOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 env_vars=None,
                 minio_operator=None,   # additional argument to make outputs of minio operator also available in container of TrainValDataSplitOperator
                 execution_timeout=None,
                 *args, **kwargs
                 ):

        # set minio operator's output dir as env variable
        if env_vars is None:
            env_vars = {}
        envs = {
            "MINIO_OPERATOR_OUT_DIR" : minio_operator.operator_out_dir if minio_operator is not None else '',
            "MINIO_OPERATOR_BUCKETNAME": minio_operator.bucket_name if minio_operator is not None else '',
            # "RATIO_TRAIN_SPLIT": dag.default_args['ui_forms']['train_split'] if dag.default_args['ui_forms']['train_split'] is not None else '',
        }
        env_vars.update(envs)
        
        super().__init__(
            dag=dag,
            name='train-val-datasplit',
            image=f"{DEFAULT_REGISTRY}/train-val-datasplit:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,      # forward newly set env variables to container
            gpu_mem_mb=24000,        # define GPU memory; default=6000
            ram_mem_mb=8000,        # and RAM memory specs to avoid K8s' OMMKilled errros; default=2000
            ram_mem_mb_lmt=24000,   # default=12000
            *args,
            **kwargs
        )