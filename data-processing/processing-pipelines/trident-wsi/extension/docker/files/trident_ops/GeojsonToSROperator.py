from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class GeojsonToSROperator(KaapanaBaseOperator):
    """
    Wraps TRIDENT's GeoJSON tissue-mask polygons as a DICOM Comprehensive 3D SR
    document (SCOORD3D regions in the slide coordinate system), referencing the
    source WSI series - purely for inspecting the segmentation result in SLIM.

    This is QC/visualization only: nothing downstream reads this SR back. The
    actual segmentation data (consumed by trident-feature-extraction) persists
    as plain GeoJSON in MinIO instead (see dag_trident_tissue_segmentation.py's
    push-to-MinIO step) - a deliberately simpler, smaller, rasterization-free
    design than the DICOM Parametric Map approach this replaced, which OOM-killed
    on real-sized WSIs regardless of how conservatively its working resolution
    was capped.

    :param dicom_operator: operator whose output dir holds the WSI's .dcm files.
    :param segmentation_operator: operator whose output dir holds the GeoJSON
        produced by TridentSegmentationOperator.
    """

    def __init__(
        self,
        dag,
        dicom_operator,
        segmentation_operator,
        name: str = "trident-geojson-to-sr",
        env_vars=None,
        execution_timeout=timedelta(minutes=15),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "TOOL": "geojson2sr",
            "DICOM_IN_DIR": dicom_operator.operator_out_dir,
            "GEOJSON_IN_DIR": segmentation_operator.operator_out_dir,
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/trident-dicom-utils:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            # Dev-cycle safeguard: this image's tag is reused across every rebuild
            # while this extension is under active development, and the cluster's
            # default pull policy (IfNotPresent) will otherwise silently keep running
            # whatever was cached on the node the first time this tag was pulled.
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            # No rasterization - but TRIDENT's raw (pre-simplification) contour
            # GeoJSON can still be large (hundreds of thousands of vertices before
            # sr_io.py simplifies it), and geopandas/GDAL's own JSON parsing has
            # real overhead on that, so keep some margin beyond the bare minimum.
            ram_mem_mb=6000,
            **kwargs,
        )
