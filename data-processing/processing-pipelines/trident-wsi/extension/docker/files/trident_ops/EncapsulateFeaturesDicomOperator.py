from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class EncapsulateFeaturesDicomOperator(KaapanaBaseOperator):
    """
    Wraps the TRIDENT feature h5 as a DICOM Raw Data Storage instance, tagged
    back to the source WSI series via ReferencedSeriesSequence, ready for
    DcmSendOperator to push to PACS.

    :param dicom_operator: operator whose output dir holds the WSI's .dcm files.
    :param features_operator: operator whose output dir holds TridentFeatureExtractionOperator's feature h5.
    :param patch_encoder: foundation-model name, only used for a human-readable SeriesDescription.
    """

    def __init__(
        self,
        dag,
        dicom_operator,
        features_operator,
        patch_encoder: str = "uni_v2",
        name: str = "trident-encapsulate-features",
        env_vars=None,
        execution_timeout=timedelta(minutes=20),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "TOOL": "encapsulate",
            "DICOM_IN_DIR": dicom_operator.operator_out_dir,
            "FEATURES_IN_DIR": features_operator.operator_out_dir,
            "PATCH_ENCODER": str(patch_encoder),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/trident-dicom-utils:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            # Dev-cycle safeguard - see GeojsonToSROperator for why.
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=4000,
            **kwargs,
        )
