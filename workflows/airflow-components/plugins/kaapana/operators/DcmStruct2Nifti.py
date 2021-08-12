from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_registry
from datetime import timedelta

class DcmStruct2Nifti(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 dicom_operator,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=1),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "DICOM_IN_DIR": str(dicom_operator.operator_out_dir) if dicom_operator is not None else str(None)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/dcmstruct2nifti:0.1.0-vdev",
            name="struct2nifti",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=100,
            ram_mem_mb_lmt=200,
            *args, **kwargs
            )
