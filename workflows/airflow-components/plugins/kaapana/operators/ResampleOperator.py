from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project, default_registry, default_project
from datetime import timedelta


class ResampleOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 format="nii.gz",
                 interpolator=1,  # 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "FORMAT": format,
            "INTERPOLATOR": str(interpolator)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/mitk-resample:04.02.2021-vdev".format(default_registry, default_project),
            name='mitk-resample',
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=2000,
            *args, **kwargs
        )
