import os 
import json
from base_utils.utils_data import get_series_to_download_from_manifest, download_from_tcia, download_from_url, list_of_series_in_dir, TEST_DATA
from base_utils.logger import get_logger
from argparse import ArgumentParser
import logging

logger = get_logger(__name__,logging.DEBUG)

def main():
    args = parser()
    series_file = args.series_file
    force_download = args.force_download
    
    all_series_to_send = []
    for testdata in TEST_DATA:
        input = testdata["input"]
        destination = testdata["destination"]

        donwload_data(input, destination, force=force_download)
        all_series_to_send += list_of_series_in_dir(destination)
        
    ## Save list of uploaded series uids
    with open(series_file,"w") as f:
        json.dump(all_series_to_send, f)

def parser():
    p = ArgumentParser()
    p.add_argument("--series-file", default="series_uids.txt")
    p.add_argument("--force-download", action="store_true",help="Force to download series even if a directory with the series_uid already exists.")
    return p.parse_args()

def donwload_data(file, destination, force=False):
    """
    Download data either from tcia or from from an url.
    File contains either a tcia manifest or an download url.
    The data is downloaded into destination.
    """
    if file.endswith(".tcia"):
        series_uids = get_series_to_download_from_manifest(file)
        logger.info("Starting to download and extract .dcm files from TCIA.")
        for series_uid in series_uids:
            series_outdir = os.path.join(destination, series_uid)
            if os.path.isdir(series_outdir) and not force:
                logger.info(f"Directory {series_outdir} already exists -> Use --force_download to download anyway.")
                continue
            download_from_tcia(series_outdir, series_uid)
            logger.info("Downloadding files ...")
        logger.info("Downloading files from TCIA completed.")
    
    elif os.path.isfile(file):
            logger.info("Downloading files from specified urls")
            download_from_url(destination, input_file=file)
            logger.info("Downloading and extracting files completed.")


if __name__=='__main__':
    main()