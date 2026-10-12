"""
Build/read a DICOM Parametric Map instance carrying a binary tissue mask, via
`highdicom.pm.ParametricMap`.

The construction approach here (explicit single-frame `plane_positions` +
`pixel_measures` computed from the source image's slide-coordinate origin and
pixel spacing, rather than highdicom's `tile_pixel_array=True` auto-tiling)
mirrors a known-working reference implementation (ParaMap_PDAC.py) rather than
relying on tile_pixel_array's own geometry inference, which produced a
badly-misaligned/oversized overlay in SLIM when first tried.
"""
import numpy as np
import pydicom
from pydicom.uid import generate_uid
import highdicom as hd
from highdicom.pm import ParametricMap, RealWorldValueMapping
from highdicom.sr.coding import CodedConcept
from highdicom import VOILUTTransformation, PlanePositionSequence, PixelMeasuresSequence, CoordinateSystemNames

MANUFACTURER = "Kaapana"
MANUFACTURER_MODEL_NAME = "trident-dicom-utils"
SOFTWARE_VERSIONS = "0.1.0"
# SLIM specifically requires this exact literal value to render a Parametric Map as a
# heatmap overlay at all - a viewer-side convention, not a DICOM standard requirement.
CONTENT_LABEL = "HEATMAP"


def _compute_derived_image_attributes(
    source_image: pydicom.Dataset,
    total_pixel_matrix: np.ndarray,
) -> "tuple[PlanePositionSequence, PixelMeasuresSequence]":
    """
    Compute the plane position/pixel measures for a single derived frame whose
    array is `total_pixel_matrix`, positioned to match `source_image`'s own
    slide-coordinate origin and total pixel matrix extent.

    Unlike a general-purpose "derive from an arbitrarily-resized map" helper,
    `total_pixel_matrix` here always has EXACTLY `source_image`'s own
    TotalPixelMatrixRows/Columns shape (we rasterize directly onto that grid,
    no resizing) - so pixel spacing is reused from the source UNCHANGED rather
    than recomputed via a rows-rounded-up-to-tile-size ratio. SLIM's pyramid
    "fit" check (dicom-microscopy-viewer's `_fitImagePyramid`, as deployed in
    SLIM v0.35.0) requires the derived image's origin AND pixel spacing to
    almost-exactly match one of the reference WSI's own pyramid levels; any
    recomputed/rounded value - even a tiny one - fails that match with "Image
    pyramid cannot be fit to reference image pyramid".
    """
    origin = source_image.TotalPixelMatrixOriginSequence[0]
    x_offset = origin.XOffsetInSlideCoordinateSystem
    y_offset = origin.YOffsetInSlideCoordinateSystem
    sm_shared_func_groups = source_image.SharedFunctionalGroupsSequence[0]
    sm_pixel_measures = sm_shared_func_groups.PixelMeasuresSequence[0]
    sm_pixel_spacing = sm_pixel_measures.PixelSpacing
    sm_slice_thickness = sm_pixel_measures.SliceThickness

    assert total_pixel_matrix.shape == (
        source_image.TotalPixelMatrixRows,
        source_image.TotalPixelMatrixColumns,
    ), "mask must exactly match source_image's own total pixel matrix shape"

    derived_pixel_spacing = (float(sm_pixel_spacing[0]), float(sm_pixel_spacing[1]))
    derived_plane_position = PlanePositionSequence(
        coordinate_system=CoordinateSystemNames.SLIDE,
        image_position=(x_offset, y_offset, 0.0),
        pixel_matrix_position=(1, 1),  # single frame
    )
    derived_pixel_measures = PixelMeasuresSequence(
        pixel_spacing=derived_pixel_spacing, slice_thickness=sm_slice_thickness
    )
    return derived_plane_position, derived_pixel_measures


def build_tissue_mask_parametric_map(
    mask: np.ndarray,
    source_level_dataset: pydicom.Dataset,
    source_series_instance_uid: str,
    series_number: int = 300,
    instance_number: int = 1,
) -> pydicom.Dataset:
    """
    :param mask: uint8/bool array, shape (rows, cols), 0=background 1=tissue, same
        shape as source_level_dataset's TotalPixelMatrixRows/Columns.
    :param source_level_dataset: the DICOM WSI pyramid-level instance the mask was
        rasterized against (see geojson_paramap.rasterize_gdf_to_level) - referenced
        as the Parametric Map's source image so SLIM can overlay it correctly.
    :param source_series_instance_uid: the ORIGINAL WSI series' SeriesInstanceUID
        (i.e. level-0, not necessarily `source_level_dataset`'s own series if that's
        a different pyramid-level instance) - explicitly stamped into
        ReferencedSeriesSequence below rather than relying on however highdicom's
        `source_images=` auto-population happens to label it, so DAG B can reliably
        resolve "which WSI series does this Parametric Map belong to" later
        (see ResolveSourceWsiOperator / resolve_source_wsi_callback).
    """
    pixel_array = mask.astype(np.float32)

    identity_mapping = RealWorldValueMapping(
        lut_label="TISSUE",
        lut_explanation="Tissue mask: 0=background, 1=tissue",
        unit=CodedConcept(value="1", scheme_designator="UCUM", meaning="no units"),
        value_range=(0.0, 1.0),
        slope=1.0,
        intercept=0.0,
    )

    plane_position, pixel_measures = _compute_derived_image_attributes(source_level_dataset, pixel_array)

    pmap = ParametricMap(
        source_images=[source_level_dataset],
        pixel_array=pixel_array,
        series_instance_uid=generate_uid(),
        series_number=series_number,
        sop_instance_uid=generate_uid(),
        instance_number=instance_number,
        manufacturer=MANUFACTURER,
        manufacturer_model_name=MANUFACTURER_MODEL_NAME,
        software_versions=SOFTWARE_VERSIONS,
        device_serial_number="n/a",
        contains_recognizable_visual_features=False,
        real_world_value_mappings=[identity_mapping],
        voi_lut_transformations=[VOILUTTransformation(window_center=0.5, window_width=1.0)],
        # Combine tiling (so the result is a proper TILED_FULL multi-frame image matching
        # the source level's own tile grid, like SLIM expects for a WSI-associated overlay)
        # with explicit plane_positions/pixel_measures for the WHOLE total pixel matrix
        # (per highdicom's own docs this is the documented, supported combination: tiling
        # is then derived automatically from this single explicit position/spacing, rather
        # than from tile_pixel_array=True's own geometry auto-inference, which produced a
        # badly oversized/misaligned overlay).
        tile_pixel_array=True,
        plane_positions=[plane_position],
        pixel_measures=pixel_measures,
        content_label=CONTENT_LABEL,
        content_description="TRIDENT tissue segmentation mask (correct via SLIM)",
        content_creator_name="Kaapana^TRIDENT",
    )

    # Explicit, robust back-reference to the original WSI series (see docstring) -
    # don't depend on exactly how highdicom's `source_images=` labels this internally.
    ref_series = pydicom.Dataset()
    ref_series.SeriesInstanceUID = source_series_instance_uid
    pmap.ReferencedSeriesSequence = [ref_series]

    return pmap


def read_mask_from_parametric_map(pmap_path: str) -> "tuple[np.ndarray, pydicom.Dataset]":
    """
    Returns (mask array thresholded at 0.5, the parametric-map Dataset itself -
    its TotalPixelMatrixColumns/Rows describe the level it was drawn against).
    """
    ds = pydicom.dcmread(pmap_path)
    pixel_array = hd.Image.from_dataset(ds).get_total_pixel_matrix(
        apply_real_world_transform=False,
        apply_voi_transform=False,
        apply_modality_transform=False,
    )

    mask = (np.squeeze(pixel_array) > 0.5).astype(np.uint8)
    return mask, ds
