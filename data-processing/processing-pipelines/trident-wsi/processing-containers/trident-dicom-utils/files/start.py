"""
Single entrypoint for the shared `trident-dicom-utils` processing-container
image (no torch - just pydicom/highdicom/geopandas conversion logic).
Dispatches on TOOL in {geojson2sr, encapsulate}.

geojson2paramap/paramap2geojson (rasterized DICOM Parametric Map round-trip)
were replaced by geojson2sr (a lightweight, vector-based Comprehensive 3D SR,
QC/visualization only) - the Parametric Map approach OOM-killed on real-sized
WSIs regardless of how conservatively the rasterization level was capped, and
the correction-and-write-back loop it existed for isn't relied upon for now.
The real segmentation data (GeoJSON) persists via MinIO instead; see
dag_trident_tissue_segmentation.py / dag_trident_feature_extraction.py.
"""
import glob
import logging
import os
import sys
from pathlib import Path

import geopandas as gpd
import pydicom

from dicom_levels import list_pyramid_levels
from sr_io import build_tissue_region_sr
from encapsulate import build_encapsulated_raw_data_instance

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trident-dicom-utils")


def iter_batch_elements(workflow_dir: str, batch_name: str):
    batch_dirs = sorted(glob.glob(os.path.join(workflow_dir, batch_name, "*")))
    if not batch_dirs:
        logger.warning("No batch-element directories found under %s/%s", workflow_dir, batch_name)
    for batch_element_dir in batch_dirs:
        yield batch_element_dir


def run_geojson_to_sr(workflow_dir: str, batch_name: str) -> None:
    dicom_in_dir = os.environ["DICOM_IN_DIR"]
    geojson_in_dir = os.environ["GEOJSON_IN_DIR"]
    operator_out_dir = os.environ["OPERATOR_OUT_DIR"]

    for batch_element_dir in iter_batch_elements(workflow_dir, batch_name):
        dicom_dir = os.path.join(batch_element_dir, dicom_in_dir)
        geojson_dir = os.path.join(batch_element_dir, geojson_in_dir)
        output_dir = os.path.join(batch_element_dir, operator_out_dir)

        geojson_files = glob.glob(os.path.join(geojson_dir, "**", "*.geojson"), recursive=True)
        # A trigger selection that (accidentally or not) includes more than just the
        # intended series creates one Kaapana batch-element per selected series - most
        # of which won't actually have real content for THIS operator. Checking isdir()
        # alone isn't enough: Kaapana pre-creates operator_out_dir as an empty directory
        # for every batch-element regardless of whether this operator's logic populates
        # it, so an unrelated/empty batch-element still passes an isdir() check. Require
        # actual .dcm files present instead.
        if not glob.glob(os.path.join(dicom_dir, "*.dcm")) or not geojson_files:
            logger.info("Skipping %s (missing dicom or geojson input)", batch_element_dir)
            continue

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        levels = list_pyramid_levels(dicom_dir)
        level0 = levels[0]
        # Full read (incl. pixel data) of level-0 is NOT needed for an SR - only its
        # header-level geometry attributes (origin, orientation, pixel spacing, frame
        # of reference), already captured in level0.dataset via stop_before_pixels=True.

        gdf = gpd.read_file(geojson_files[0])
        logger.info("GeoJSON feature count: %d", len(gdf))

        if gdf.empty:
            logger.warning("Empty GeoJSON mask for %s - skipping SR creation", batch_element_dir)
            continue

        sr_ds = build_tissue_region_sr(gdf, level0.dataset)
        out_path = os.path.join(output_dir, f"{sr_ds.SOPInstanceUID}_sr.dcm")
        sr_ds.save_as(out_path, write_like_original=False)
        logger.info("Wrote tissue-region SR: %s", out_path)


def run_encapsulate(workflow_dir: str, batch_name: str) -> None:
    dicom_in_dir = os.environ["DICOM_IN_DIR"]
    features_in_dir = os.environ["FEATURES_IN_DIR"]
    operator_out_dir = os.environ["OPERATOR_OUT_DIR"]
    patch_encoder = os.getenv("PATCH_ENCODER", "unknown")

    for batch_element_dir in iter_batch_elements(workflow_dir, batch_name):
        dicom_dir = os.path.join(batch_element_dir, dicom_in_dir)
        features_dir = os.path.join(batch_element_dir, features_in_dir)
        output_dir = os.path.join(batch_element_dir, operator_out_dir)

        feature_files = glob.glob(os.path.join(features_dir, "**", "*.h5"), recursive=True)
        if not glob.glob(os.path.join(dicom_dir, "*.dcm")) or not feature_files:
            logger.info("Skipping %s (missing dicom or feature-h5 input)", batch_element_dir)
            continue

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        levels = list_pyramid_levels(dicom_dir)
        level0_full_ds = pydicom.dcmread(levels[0].path, stop_before_pixels=True)

        with open(feature_files[0], "rb") as f:
            payload_bytes = f.read()

        ds = build_encapsulated_raw_data_instance(
            payload_bytes=payload_bytes,
            source_level0_dataset=level0_full_ds,
            series_description=f"TRIDENT features ({patch_encoder})",
            content_description=os.path.basename(feature_files[0]),
        )
        out_path = os.path.join(output_dir, f"{ds.SOPInstanceUID}.dcm")
        ds.save_as(out_path, write_like_original=False)
        logger.info("Wrote encapsulated feature-h5 DICOM instance: %s", out_path)


def main() -> None:
    tool = os.getenv("TOOL")
    if tool not in ("geojson2sr", "encapsulate"):
        logger.error("TOOL must be one of 'geojson2sr', 'encapsulate' (got %r)", tool)
        sys.exit(1)

    workflow_dir = os.environ["WORKFLOW_DIR"]
    batch_name = os.environ["BATCH_NAME"]

    logger.info("Starting trident-dicom-utils tool=%s workflow_dir=%s batch_name=%s", tool, workflow_dir, batch_name)

    if tool == "geojson2sr":
        run_geojson_to_sr(workflow_dir, batch_name)
    elif tool == "encapsulate":
        run_encapsulate(workflow_dir, batch_name)

    logger.info("tool=%s done.", tool)


if __name__ == "__main__":
    main()
