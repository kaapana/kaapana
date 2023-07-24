from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class Mask2nifitiOperator(KaapanaBaseOperator):
    """
    This operator takes a .dcm SEG or RTSTRUCT file and converts it into the Nifti file format.
    For DICOM SEG, the operator uses the dcmqi libary (https://qiicr.gitbook.io/dcmqi-guide/).
    For DICOM RTSTRUCT, the operator uses the dcmrtstruct2nii libary (https://github.com/Sikerdebaard/dcmrtstruct2nii).

    **Inputs:**
    * .dcm mask-file (SEG and RTSTRUCT are supported)

    **Outputs:**
    * Nifti file with the segmentation mask
    """

    def __init__(
        self,
        dag,
        dicom_operator=None,
        output_type="nii.gz",
        seg_filter=None,
        exit_on_error=True,
        env_vars=None,
        execution_timeout=timedelta(days=5),
        **kwargs,
    ):
        """
        :param seg_filter: A bash list of organs, that should be filtered from the segmentation e.g. "liver,aorta"
        :param env_vars: Environmental variables
        :param execution_timeout: max time allowed for the execution of this task instance, if it goes beyond it will raise and fail
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "BASE_DICOM_DIR": str(dicom_operator.operator_out_dir)
            if dicom_operator is not None
            else str(None),
            "OUTPUT_TYPE": output_type,
            "SEG_FILTER": seg_filter or "",  # a bash list i.e.: 'liver,aorta',
            "EXIT_ON_ISSUE": str(exit_on_error),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/mask2nifti:{KAAPANA_BUILD_VERSION}",
            name="mask2nifti",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            ram_mem_mb_lmt=20000,
            **kwargs,
        )
