import os
from pathlib import Path
from base_utils.utils_data import (
    get_series_to_download_from_manifest,
    download_from_tcia,
    download_from_url,
)
from base_utils.logger import get_logger
from argparse import ArgumentParser
import logging

logger = get_logger(__name__, logging.DEBUG)


def main():
    args = parser()
    force_download = args.force_download
    input = args.input
    target_dir = args.output
    donwload_data(input, target_dir, force=force_download)


def parser():
    p = ArgumentParser()
    p.add_argument("--output", default=".", help="Output directory.")
    p.add_argument(
        "--force-download",
        action="store_true",
        help="Force to download series even if a directory with the series_uid already exists.",
    )
    p.add_argument("--input")
    return p.parse_args()


def donwload_data(file, target_dir, force=False):
    """
    Download data either from tcia or from from an url.
    File contains either a tcia manifest or a download url.
    The data is downloaded into target_dir.
    Parameter force determines, whether to force download, even if the directories per series already exist.
    """
    if file.endswith(".tcia"):
        series_uids = get_series_to_download_from_manifest(file)
        logger.info("Starting to download and extract .dcm files from TCIA.")
        for series_uid in series_uids:
            series_outdir = os.path.join(target_dir, series_uid)
            if os.path.isdir(series_outdir) and not force:
                logger.info(
                    f"Directory {series_outdir} already exists -> Use --force_download to download anyway."
                )
                continue
            download_from_tcia(series_outdir, series_uid)
            logger.info("Downloadding files ...")
        logger.info("Downloading files from TCIA completed.")

    elif os.path.isfile(file):
        if force or len([f for f in Path(target_dir).glob("**/*.dcm")]) == 0:
            logger.info("Downloading files from specified urls")
            download_from_url(target_dir, input_file=file)
            logger.info("Downloading and extracting files completed.")
        else:
            logger.info(
                f"Dicom files found in {target_dir=}. Skip download. Use --force to force download."
            )


if __name__ == "__main__":
    main()
