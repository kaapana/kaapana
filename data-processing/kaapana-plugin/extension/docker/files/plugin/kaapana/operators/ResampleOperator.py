from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_platform_abbr, default_platform_version
from datetime import timedelta


class ResampleOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 original_img_operator,
                 original_img_batch_name=None,
                 format="nii.gz",
                 interpolator=1,  # 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
                 copy_target_data=False,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=320),
                 **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "FORMAT": format,
            "ORG_IMG_IN_DIR": str(original_img_operator.operator_out_dir),
            "ORG_IMG_BATCH_NAME": str(original_img_batch_name),
            "COPY_DATA": str(copy_target_data),
            "INTERPOLATOR": str(interpolator)
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/mitk-resample:{default_platform_abbr}_{default_platform_version}__2021-02-18",
            name='mitk-resample',
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=2000,
            **kwargs
        )
