"""
Conversion between TRIDENT's GeoJSON tissue-mask format and a DICOM Parametric
Map instance, so the mask can be viewed/corrected in SLIM.

Coordinate convention (confirmed by reading TRIDENT's actual source,
trident/wsi_objects/WSI.py:segment_tissue and trident/IO.py:mask_to_gdf, at the
commit this was written against): TRIDENT always passes
`contour_scale=1/mpp_reduction_factor` into `mask_to_gdf`, which makes the
*saved* GeoJSON polygon coordinates land in plain LEVEL-0 (base/full-resolution)
pixel space, regardless of what magnification segmentation ran at internally.
`tissue_seg_path=`/`gdf_contours` is then consumed directly as level-0 pixel
coordinates elsewhere (WSIPatcher's mask-overlap check). So this module only
ever has to scale between "level-0 pixel space" and "chosen DICOM pyramid
level's pixel space" - a plain ratio of TotalPixelMatrixColumns, nothing else.

If a future TRIDENT_GIT_REF changes this invariant, re-derive it the same way
(read segment_tissue's mask_to_gdf call) before trusting this module again.
"""
from typing import Tuple

import cv2
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from shapely import affinity
from rasterio import features as rio_features

from dicom_levels import DicomLevel


def rasterize_gdf_to_level(
    gdf: gpd.GeoDataFrame,
    level0_width: int,
    level0_height: int,
    level: DicomLevel,
) -> np.ndarray:
    """
    Rasterize level-0-pixel-space polygons onto `level`'s own pixel grid.
    Returns a uint8 array (0/1), shape (level.rows, level.cols).
    """
    scale = level.total_pixel_matrix_columns / level0_width

    if gdf.empty:
        return np.zeros((level.total_pixel_matrix_rows, level.total_pixel_matrix_columns), dtype=np.uint8)

    scaled_geoms = [affinity.scale(geom, xfact=scale, yfact=scale, origin=(0, 0)) for geom in gdf.geometry]

    mask = rio_features.rasterize(
        shapes=[(geom, 1) for geom in scaled_geoms],
        out_shape=(level.total_pixel_matrix_rows, level.total_pixel_matrix_columns),
        fill=0,
        dtype="uint8",
    )
    return mask


def vectorize_mask_to_geojson(
    mask: np.ndarray,
    level0_width: int,
) -> gpd.GeoDataFrame:
    """
    Inverse of rasterize_gdf_to_level: vectorize a (possibly SLIM-corrected) raster
    mask back into a GeoDataFrame in level-0 pixel space, ready to be written as a
    GeoJSON that TRIDENT can consume via `tissue_seg_path=`.

    Deliberately scales using `mask.shape` itself (not a DicomLevel's DICOM
    attributes) - the mask array read back out of the Parametric Map is the only
    thing we can fully trust the resolution of; whether highdicom labelled that
    instance's own TotalPixelMatrixColumns/Rows vs. plain Rows/Columns depends on
    whether it was built as a tiled WSI-style instance (see paramap_io.py's
    top-of-file caveat), so avoid depending on either here.
    """
    mask_width = mask.shape[1]
    scale_to_level0 = level0_width / mask_width

    binary = (mask > 0).astype(np.uint8) * 255
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

    if not contours:
        return gpd.GeoDataFrame(columns=["tissue_id", "geometry"])

    hierarchy = np.squeeze(hierarchy, axis=0)  # (N, 4): next, prev, first_child, parent

    polygons = []
    tissue_ids = []
    next_id = 0
    for idx, contour in enumerate(contours):
        parent = hierarchy[idx][3]
        if parent != -1:
            continue  # this is a hole, attached to its parent polygon below
        if len(contour) < 3:
            continue

        exterior = contour.squeeze(1) * scale_to_level0

        holes = []
        child = hierarchy[idx][2]
        while child != -1:
            if len(contours[child]) >= 3:
                holes.append(contours[child].squeeze(1) * scale_to_level0)
            child = hierarchy[child][0]

        polygon = Polygon(exterior, holes=holes if holes else None)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        polygons.append(polygon)
        tissue_ids.append(next_id)
        next_id += 1

    gdf = gpd.GeoDataFrame(pd.DataFrame(tissue_ids, columns=["tissue_id"]), geometry=polygons)
    gdf.set_crs("EPSG:3857", inplace=True)
    return gdf


def target_mpp_for_magnification(target_mag: int) -> float:
    """Mirrors TRIDENT's own `destination_mpp = 10 / target_mag` convention."""
    return 10.0 / target_mag
