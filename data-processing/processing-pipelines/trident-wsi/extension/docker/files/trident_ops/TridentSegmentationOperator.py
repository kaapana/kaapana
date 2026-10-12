from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class TridentSegmentationOperator(KaapanaBaseOperator):
    """
    Runs TRIDENT's tissue-segmentation stage (trident.WSI.segment_tissue) on one
    DICOM WSI series, writing the result as a GeoJSON tissue-mask contour file.

    - Code: https://github.com/mahmoodlab/trident

    :param dicom_operator: operator whose output dir holds the WSI's .dcm files.
    :param segmenter_model: one of TRIDENT's trident.segmentation_models.load.segmentation_model_factory
        keys, e.g. "hest" (default) or "grandqc".
    :param confidence_thresh: softmax confidence threshold for the binary tissue mask.
    :param seg_mag: magnification TRIDENT segments at.
    :param holes_are_tissue: whether holes inside tissue contours are treated as tissue.
    """

    def __init__(
        self,
        dag,
        dicom_operator,
        segmenter_model: str = "hest",
        confidence_thresh: float = 0.5,
        seg_mag: int = 10,
        holes_are_tissue: bool = False,
        name: str = "trident-tissue-segmentation",
        env_vars=None,
        execution_timeout=timedelta(minutes=60),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "TRIDENT_STAGE": "seg",
            "SEGMENTER_MODEL": str(segmenter_model),
            "CONFIDENCE_THRESH": str(confidence_thresh),
            "SEG_MAG": str(seg_mag),
            "HOLES_ARE_TISSUE": str(holes_are_tissue),
        }
        env_vars.update(envs)

        if "labels" not in kwargs or not isinstance(kwargs["labels"], dict):
            kwargs["labels"] = {}
        # HuggingFace download of segmentation-model weights needs outbound internet.
        kwargs["labels"]["network-access-external-ips"] = "true"

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
            enable_proxy=True,
            ram_mem_mb=16000,
            ram_mem_mb_lmt=32000,
            gpu_mem_mb=8000,
            retries=1,
            **kwargs,
        )
