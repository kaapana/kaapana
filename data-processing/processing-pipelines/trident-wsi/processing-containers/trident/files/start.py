"""
Single entrypoint for the shared `trident` processing-container image.
Dispatches on TRIDENT_STAGE in {seg, coords, feat} - see the three
Trident*Operator classes in extension/docker/files/trident_ops/ for how each
stage's env vars are populated per Kaapana DAG run.

Standard Kaapana batch-element convention: WORKFLOW_DIR/BATCH_NAME/<series-uid>/<operator_in_dir>
-> .../<operator_out_dir>. This script processes one batch-element (one slide) at a time.
"""
import os
import sys
import logging
from glob import glob
from pathlib import Path

import torch

from trident import load_wsi
from trident.segmentation_models import segmentation_model_factory
from trident.patch_encoder_models import encoder_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trident-op")


def wsi_name_from_series_uid(series_uid: str) -> str:
    """
    A safe identifier for TRIDENT's `name=` parameter (used to name every
    output artifact: GeoJSON, patch-coord h5, feature h5), derived from a
    Kaapana batch-element directory name - always the series UID.

    Can't just pass the UID through as-is: TRIDENT applies os.path.splitext()
    to `name` internally, and a DICOM UID is itself dot-separated, so the
    text after its LAST dot gets silently treated as a bogus file extension
    and dropped (confirmed: this installation's UIDs all share one long root,
    so every series collided onto the identical truncated name). Swapping
    dots for underscores avoids that, but keeps the same length - the
    encapsulated DICOM's ContentDescription element (VR LO, 64-char hard
    limit) then overflows for any reasonably long UID + ".h5" (confirmed via
    a real pydicom length-validation warning).

    Using just the UID's final dot-segment solves both: it has no dots left
    to confuse splitext(), and it's short. It's also still the actual
    differentiating part for UIDs from pydicom.generate_uid() (a fixed
    shared root + one long unique numeric tail), which is what populates
    every UID in this Kaapana installation.
    """
    tail = series_uid.rsplit(".", 1)[-1]
    return tail[:55]  # headroom under ContentDescription's 64-char cap


def getenv_bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("true", "1", "t", "yes")


def getenv_float(key: str, default: float) -> float:
    val = os.getenv(key)
    return float(val) if val not in (None, "", "None") else default


def getenv_int(key: str, default: int) -> int:
    val = os.getenv(key)
    return int(val) if val not in (None, "", "None") else default


def device_str() -> str:
    cuda_devices = os.getenv("CUDA_VISIBLE_DEVICES", "")
    return "cuda:0" if cuda_devices and torch.cuda.is_available() else "cpu"


def iter_batch_elements(workflow_dir: str, batch_name: str):
    batch_dirs = sorted(glob(os.path.join(workflow_dir, batch_name, "*")))
    if not batch_dirs:
        logger.warning("No batch-element directories found under %s/%s", workflow_dir, batch_name)
    for batch_element_dir in batch_dirs:
        yield batch_element_dir


def run_segmentation(workflow_dir: str, batch_name: str) -> None:
    operator_in_dir = os.environ["OPERATOR_IN_DIR"]
    operator_out_dir = os.environ["OPERATOR_OUT_DIR"]

    segmenter_model = os.getenv("SEGMENTER_MODEL", "hest")
    confidence_thresh = getenv_float("CONFIDENCE_THRESH", 0.5)
    seg_mag = getenv_int("SEG_MAG", 10)
    holes_are_tissue = getenv_bool("HOLES_ARE_TISSUE", True)

    model = segmentation_model_factory(segmenter_model, confidence_thresh=confidence_thresh)

    for batch_element_dir in iter_batch_elements(workflow_dir, batch_name):
        dicom_dir = os.path.join(batch_element_dir, operator_in_dir)
        output_dir = os.path.join(batch_element_dir, operator_out_dir)
        # A trigger selection including more than just the intended series creates one
        # Kaapana batch-element per selected series; Kaapana pre-creates operator_out_dir
        # as an empty dir for every batch-element regardless of content, so isdir() alone
        # isn't a reliable "is this batch-element real" check - require actual .dcm files.
        if not glob(os.path.join(dicom_dir, "*.dcm")):
            logger.info("Skipping %s (no input dir)", batch_element_dir)
            continue

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Segmenting tissue for %s", dicom_dir)

        # name=<series UID>: TRIDENT otherwise names every output artifact (GeoJSON,
        # patch-coord h5, feature h5) after slide_path's own basename - which, in
        # Kaapana's batch-element layout, is always literally "get-input-data" (the
        # fixed operator-output-dir name), not anything slide-specific. The batch-
        # element directory's own name is the series UID (Kaapana's batch convention:
        # WORKFLOW_DIR/BATCH_NAME/<series-uid>/<operator_dir>), so use that instead.
        # splitext() (os.path.splitext()'s convention) would otherwise mangle a raw
        # UID: it treats everything after a dotted UID's LAST dot as a bogus file
        # extension, e.g. "1.2.826.0.1.3680043.8.498.22375997..." -> name truncated
        # to "1.2.826.0.1.3680043.8.498", dropping the part that actually makes it
        # unique (confirmed: this installation's UIDs all share that root, so every
        # series would collide onto the identical truncated name). Dots -> underscores
        # avoids giving splitext() anything to misinterpret.
        wsi_name = wsi_name_from_series_uid(os.path.basename(batch_element_dir))
        wsi = load_wsi(slide_path=dicom_dir, reader_type="dicom", lazy_init=False, name=wsi_name)
        # DIAGNOSTIC (temporary): cross-check against trident-dicom-utils' independent
        # "level0" determination (via raw pydicom TotalPixelMatrixColumns sorting) - a
        # mismatch here would mean the GeoJSON's level-0 coordinate space doesn't match
        # what the rasterization step treats as level-0, producing a wrong scale factor.
        logger.info(
            "DEBUG DicomWSI base dims: width=%d height=%d mpp=%.4f mag=%s level_count=%d",
            wsi.width, wsi.height, wsi.mpp, wsi.mag, wsi.level_count,
        )
        logger.info("DEBUG DicomWSI level_dimensions: %s", wsi.level_dimensions)
        wsi.segment_tissue(
            segmentation_model=model,
            target_mag=getattr(model, "target_mag", seg_mag),
            job_dir=output_dir,
            holes_are_tissue=holes_are_tissue,
            device=device_str(),
        )
        wsi.close()
        logger.info("Wrote GeoJSON contours under %s/contours_geojson/", output_dir)


def run_patching(workflow_dir: str, batch_name: str) -> None:
    operator_in_dir = os.environ["OPERATOR_IN_DIR"]  # WSI pixel data (.dcm)
    geojson_in_dir = os.environ["GEOJSON_IN_DIR"]  # tissue mask (contours_geojson/*.geojson)
    operator_out_dir = os.environ["OPERATOR_OUT_DIR"]

    target_magnification = getenv_int("TARGET_MAGNIFICATION", 20)
    patch_size = getenv_int("PATCH_SIZE", 256)
    overlap = getenv_int("OVERLAP", 0)
    min_tissue_proportion = getenv_float("MIN_TISSUE_PROPORTION", 0.0)

    for batch_element_dir in iter_batch_elements(workflow_dir, batch_name):
        dicom_dir = os.path.join(batch_element_dir, operator_in_dir)
        geojson_dir = os.path.join(batch_element_dir, geojson_in_dir)
        output_dir = os.path.join(batch_element_dir, operator_out_dir)
        if not glob(os.path.join(dicom_dir, "*.dcm")):
            logger.info("Skipping %s (no WSI input dir)", batch_element_dir)
            continue

        geojson_files = glob(os.path.join(geojson_dir, "**", "*.geojson"), recursive=True)
        if not geojson_files:
            logger.warning("No tissue-mask GeoJSON found under %s - skipping %s", geojson_dir, batch_element_dir)
            continue

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Extracting patch coords for %s using mask %s", dicom_dir, geojson_files[0])

        # name=<series UID, dots sanitized> - see run_segmentation's comment for why.
        wsi_name = wsi_name_from_series_uid(os.path.basename(batch_element_dir))
        wsi = load_wsi(
            slide_path=dicom_dir,
            reader_type="dicom",
            tissue_seg_path=geojson_files[0],
            lazy_init=False,
            name=wsi_name,
        )
        wsi.extract_tissue_coords(
            target_mag=target_magnification,
            patch_size=patch_size,
            save_coords=output_dir,
            overlap=overlap,
            min_tissue_proportion=min_tissue_proportion,
        )
        wsi.close()
        logger.info("Wrote patch coordinates under %s", output_dir)


def run_feature_extraction(workflow_dir: str, batch_name: str) -> None:
    operator_in_dir = os.environ["OPERATOR_IN_DIR"]  # WSI pixel data (.dcm)
    coords_in_dir = os.environ["COORDS_IN_DIR"]  # TridentPatchingOperator output
    operator_out_dir = os.environ["OPERATOR_OUT_DIR"]

    patch_encoder_name = os.getenv("PATCH_ENCODER", "uni_v2")
    batch_limit = getenv_int("BATCH_LIMIT", 64)

    hf_token = os.getenv("HF_TOKEN", "")
    if hf_token and hf_token.lower() != "none":
        # huggingface_hub automatically picks up HF_TOKEN from the environment -
        # no explicit login() call needed (and none should be hardcoded, see the plan).
        os.environ["HF_TOKEN"] = hf_token

    device = device_str()
    encoder = encoder_factory(patch_encoder_name)
    encoder.eval().to(device)

    for batch_element_dir in iter_batch_elements(workflow_dir, batch_name):
        dicom_dir = os.path.join(batch_element_dir, operator_in_dir)
        coords_dir = os.path.join(batch_element_dir, coords_in_dir)
        output_dir = os.path.join(batch_element_dir, operator_out_dir)
        if not glob(os.path.join(dicom_dir, "*.dcm")):
            logger.info("Skipping %s (no WSI input dir)", batch_element_dir)
            continue

        coords_files = glob(os.path.join(coords_dir, "**", "patches", "*_patches.h5"), recursive=True)
        if not coords_files:
            logger.warning("No patch-coordinate h5 found under %s - skipping %s", coords_dir, batch_element_dir)
            continue

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Extracting %s features for %s using coords %s", patch_encoder_name, dicom_dir, coords_files[0])

        # max_workers=0: extract_patch_features() reads patches via a DataLoader
        # whose worker processes (when num_workers > 0, TRIDENT's default - see
        # trident.IO.get_num_workers) call DicomWSI.read_region() after a fork.
        # Our DicomWSI backend wraps a wsidicom.WsiDicom instance that was never
        # tested under multiprocessing, and real output confirmed the failure
        # mode: of 4619 extracted patches from one run, 4398 (95%) came back as
        # one single byte-identical feature vector, spanning coordinates across
        # almost the entire slide - i.e. most worker-read patches were silently
        # wrong/duplicated, not an inference problem. Forcing single-process
        # reading avoids the fork entirely.
        # name=<series UID, dots sanitized> - see run_segmentation's comment for why.
        wsi_name = wsi_name_from_series_uid(os.path.basename(batch_element_dir))
        wsi = load_wsi(
            slide_path=dicom_dir, reader_type="dicom", lazy_init=False, max_workers=0, name=wsi_name
        )
        wsi.extract_patch_features(
            patch_encoder=encoder,
            coords_path=coords_files[0],
            save_features=output_dir,
            device=device,
            saveas="h5",
            batch_limit=batch_limit,
        )
        wsi.close()
        logger.info("Wrote feature h5 under %s", output_dir)


def main() -> None:
    stage = os.getenv("TRIDENT_STAGE")
    if stage not in ("seg", "coords", "feat"):
        logger.error("TRIDENT_STAGE must be one of 'seg', 'coords', 'feat' (got %r)", stage)
        sys.exit(1)

    workflow_dir = os.environ["WORKFLOW_DIR"]
    batch_name = os.environ["BATCH_NAME"]

    logger.info("Starting TRIDENT stage=%s workflow_dir=%s batch_name=%s", stage, workflow_dir, batch_name)

    if stage == "seg":
        run_segmentation(workflow_dir, batch_name)
    elif stage == "coords":
        run_patching(workflow_dir, batch_name)
    elif stage == "feat":
        run_feature_extraction(workflow_dir, batch_name)

    logger.info("TRIDENT stage=%s done.", stage)


if __name__ == "__main__":
    main()
