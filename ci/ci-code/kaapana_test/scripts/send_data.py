#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path

from kaapana_test.send_data.utils_data import DataEndpoints, download_data, send_data
from kaapana_test.utils.logger import get_logger

logger = get_logger("send_data", logging.DEBUG)


def main():
    p = argparse.ArgumentParser(
        description="Download and send test datasets to Kaapana"
    )
    p.add_argument(
        "--client-secret", required=True, help="Client secret for Kaapana API access"
    )
    p.add_argument("--host", required=True, help="Kaapana hostname)")
    p.add_argument(
        "--timeout", type=int, default=300, help="Max wait time per dataset (seconds)"
    )
    p.add_argument(
        "--source-directory",
        required=True,
        help="Folder containing the dataset-info (tcia manifests)",
    )
    p.add_argument(
        "--download-directory",
        required=True,
        help="Directory to store downloaded datasets ",
    )
    p.add_argument("--force-download", action="store_true")
    args = p.parse_args()

    datasets = [
        {"kaapana_dataset": dataset.stem, "source_file": str(dataset)}
        for dataset in Path(args.source_directory).glob("*.tcia")
    ] + [
        {"kaapana_dataset": dataset.stem, "source_file": str(dataset)}
        for dataset in Path(args.source_directory).glob("*.url")
    ]

    for dataset in datasets:
        # DOWNLOAD
        logger.info(f"Downloading dataset: {dataset['kaapana_dataset']}")
        download_data(
            dataset, Path(args.download_directory) / dataset["kaapana_dataset"], force=args.force_download
        )
        logger.info(Path(args.download_directory) / dataset["kaapana_dataset"])
        # SEND
        send_data(Path(args.download_directory) / dataset["kaapana_dataset"], args.host, dataset)

        # WAIT FOR INGESTION
        DataEndpoints(args.host, args.client_secret).wait_for_dataset(dataset)


if __name__ == "__main__":
    raise SystemExit(main())
