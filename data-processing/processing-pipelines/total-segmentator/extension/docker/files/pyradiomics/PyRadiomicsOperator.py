from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class PyRadiomicsOperator(KaapanaBaseOperator):
    """
    Calculates Radiomics feature for given nifti segmentation masks using pyradiomics.

    The operator can work with both, multi-mask and single-mask nifti files, but the indicated use is with multiple
    single-mask nifti files, so that the radiomics features will be calculated per class.

    Default behaviour is only shape and first order features.

    - Publication:
      Van Griethuysen, J. J., Fedorov, A., Parmar, C., Hosny, A., Aucoin, N., Narayan, V., ... & Aerts, H. J. (2017).
      Computational radiomics system to decode the radiographic phenotype.
      Cancer research, 77(21), e104-e107.
    - Code: https://pyradiomics.readthedocs.io/en/latest/
    """

    def __init__(self,
                 dag,
                 segmentation_operator,
                 alg_name=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 **kwargs):
        if env_vars is None:
            env_vars = {}

        envs = {
            # directory that contains the segmentation objects
            "OPERATOR_IN_SEGMENATIONS_DIR": segmentation_operator.operator_out_dir,
            "ALGORITHM_NAME": f'{alg_name or "kaapana"}',
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/pyradiomics:{KAAPANA_BUILD_VERSION}",
            name="pyradiomics",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            ram_mem_mb_lmt=6000,
            **kwargs
        )
