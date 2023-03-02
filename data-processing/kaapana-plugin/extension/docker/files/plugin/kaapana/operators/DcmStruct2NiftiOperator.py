from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from datetime import timedelta

class DcmStruct2NiftiOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 dicom_operator,
                 seg_filter=None,
                 env_vars=None,
                 execution_timeout=timedelta(hours=6),
                 **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "DICOM_IN_DIR": str(dicom_operator.operator_out_dir) if dicom_operator is not None else str(None),
            "SEG_FILTER": seg_filter or '', # a bash list i.e.: 'liver,aorta'
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/dcmstruct2nifti:{KAAPANA_BUILD_VERSION}",
            name="struct2nifti",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=500,
            ram_mem_mb_lmt=1000,
            **kwargs
            )
