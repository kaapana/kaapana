from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project, default_registry, default_project
from datetime import timedelta

class DcmSeg2ItkOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 output_type=None,
                 seg_filter=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=5),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "OUTPUT_TYPE": output_type or 'nrrd',
            "SEG_FILTER": seg_filter or '', # a bash list i.e.: 'liver aorta'
            "DCMQI_COMMAND": "segimage2itkimage",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/dcmqi:v1.2.2".format(default_registry, default_project),
            name="dcmseg2nrrd",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            *args, **kwargs
            )
