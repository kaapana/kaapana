from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project, default_registry, default_project
from datetime import timedelta


class DcmConverterOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 output_format="nrrd",
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "CONVERTTO": output_format,
        }

        env_vars.update(envs)

        if output_format != "nrrd" and (output_format != "nii.gz" and output_format != "nii"):
            print(("output format %s is currently not supported!" % output_format))
            print("Dcm2nrrdOperator options: 'nrrd' or 'nii'")
            exit(1)

        super().__init__(
            dag=dag,
            image="{}{}/mitk-fileconverter:2021-02-18-vdev".format(default_registry, default_project),
            name='dcm-converter',
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=2000,
            ram_mem_mb_lmt=12000,
            *args, **kwargs
        )
