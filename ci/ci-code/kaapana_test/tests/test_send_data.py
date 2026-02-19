#!/usr/bin/env python3
import logging
from pathlib import Path

from kaapana_test.data import DataEndpoints, download_data, send_data
from kaapana_test.utils.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


def test_send_data(
    host, data_endpoints: DataEndpoints, dataset, download_directory, force_download
):
    source_file = dataset
    kaapana_dataset = dataset.stem[:16]
    # DOWNLOAD
    logger.info(f"Downloading dataset: {kaapana_dataset}")
    logger.info(f"Download directory: {download_directory}")
    download_data(
        source_file,
        Path(download_directory) / kaapana_dataset,
        force=force_download,
    )
    # SEND
    send_data(Path(download_directory) / kaapana_dataset, host, kaapana_dataset)
    # WAIT FOR INGESTION
    try:
        data_endpoints.wait_for_dataset(source_file, kaapana_dataset)
    except TimeoutError:
        assert False
