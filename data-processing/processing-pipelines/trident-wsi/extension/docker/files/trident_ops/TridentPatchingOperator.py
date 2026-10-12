from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class TridentPatchingOperator(KaapanaBaseOperator):
    """
    Runs TRIDENT's patch-coordinate extraction stage (trident.WSI.extract_tissue_coords),
    restricted to the tissue mask - i.e. "the selected region".

    :param dicom_operator: operator whose output dir holds the WSI's .dcm files.
    :param geojson_operator: operator whose output dir holds the TRIDENT-compatible
        GeoJSON mask (pulled from MinIO - see dag_trident_feature_extraction.py).
    :param target_magnification: magnification to extract patches at.
    :param patch_size: patch side length in pixels at target_magnification.
    :param overlap: patch overlap in pixels.
    :param min_tissue_proportion: minimum tissue-overlap fraction for a patch to be kept.
    """

    def __init__(
        self,
        dag,
        dicom_operator,
        geojson_operator,
        target_magnification: int = 20,
        patch_size: int = 256,
        overlap: int = 0,
        min_tissue_proportion: float = 0.0,
        name: str = "trident-patching",
        env_vars=None,
        execution_timeout=timedelta(minutes=60),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "TRIDENT_STAGE": "coords",
            "GEOJSON_IN_DIR": geojson_operator.operator_out_dir,
            "TARGET_MAGNIFICATION": str(target_magnification),
            "PATCH_SIZE": str(patch_size),
            "OVERLAP": str(overlap),
            "MIN_TISSUE_PROPORTION": str(min_tissue_proportion),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            input_operator=dicom_operator,
            image=f"{DEFAULT_REGISTRY}/trident:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            # Dev-cycle safeguard - see GeojsonToSROperator for why.
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=16000,
            ram_mem_mb_lmt=32000,
            retries=1,
            **kwargs,
        )
