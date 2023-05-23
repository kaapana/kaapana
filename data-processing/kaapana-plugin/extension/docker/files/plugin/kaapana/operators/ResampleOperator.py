from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class ResampleOperator(KaapanaBaseOperator):
    """
    Operator to resample NIFTI images.

    This operator resamples NIFTI images (.nii.gz file format) according to a defined shape served by a template image.
    The resampling is executed using MITK's "MitkCLResampleImageToReference.sh".
    The resampling is executed without additional registration.
    Possible interpolator types are a linear interpolator (0), a nearest neighbor interpolator (1) and a sinc interpolator (2).

    **Inputs:**

    * input_operator: Data which should be resampled.
    * original_img_operator: Data element which serves as a shape template for the to-be-resampled input data.
    * operator_out_dir: Directory in which the resampled data is saved.

    **Outputs:**

    * resampled NIFTI images
    """

    def __init__(
        self,
        dag,
        original_img_operator,
        original_img_batch_name=None,
        format="nii.gz",
        interpolator=1,  # 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
        copy_target_data=False,
        env_vars=None,
        execution_timeout=timedelta(minutes=320),
        **kwargs,
    ):
        """
        :param original_img_operator: Data element which serves as a shape template for the to-be-resampled input data.
        :param original_img_batch_name: Batch nahem of template data element.
        :param format: = .nii.gz NIFTI image format.
        :param interpolator: Interpolation mechanism to resample input images according to reference image's shape. 0 = linear (default), 1 = nearest neighbor, 2 = sinc.
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "FORMAT": format,
            "ORG_IMG_IN_DIR": str(original_img_operator.operator_out_dir),
            "ORG_IMG_BATCH_NAME": str(original_img_batch_name),
            "COPY_DATA": str(copy_target_data),
            "INTERPOLATOR": str(interpolator),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/mitk-resample:{KAAPANA_BUILD_VERSION}",
            name="mitk-resample",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=2000,
            **kwargs,
        )
