from base_utils.utils_data import send_data_to_platform
from base_utils.logger import get_logger
from argparse import ArgumentParser
import os, sys, logging

logger = get_logger(__name__, logging.DEBUG)


def main():
    args = parser()
    host = args.host
    client_secret = args.client_secret or os.environ.get("CLIENT_SECRET", None)
    if not client_secret:
        logger.error(
            "A client secret has to be specified by command line flag or as environment variable CLIENT_SECRET"
        )
        sys.exit(1)

    directory = args.source
    aetitle = args.dataset
    send_data_to_platform(directory, host, aetitle)


def parser():
    p = ArgumentParser()
    p.add_argument(
        "--host", required=True, default=None, help="Host URL of the Kaapana instance."
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="The client secret of the kaapana client in keycloak.",
    )
    p.add_argument("--source", help="Directory containing dicom data.")
    p.add_argument("--dataset", help="Name of the dataset to store the series.")
    return p.parse_args()


if __name__ == "__main__":
    main()
