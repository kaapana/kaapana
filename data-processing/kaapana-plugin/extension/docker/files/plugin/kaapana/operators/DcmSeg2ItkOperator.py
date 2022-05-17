from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_platform_abbr, default_platform_version
from datetime import timedelta

class DcmSeg2ItkOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 output_format=None,
                 seg_filter=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "OUTPUT_TYPE": output_format or 'nrrd',
            "SEG_FILTER": seg_filter or '', # a bash list i.e.: 'liver,aorta'
            "DCMQI_COMMAND": "segimage2itkimage",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/dcmqi:{default_platform_abbr}_{default_platform_version}__v1.2.4",
            name="dcmseg2nrrd",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            ram_mem_mb_lmt=20000,
             **kwargs
            )
