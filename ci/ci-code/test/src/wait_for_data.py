from base_utils.utils_data import DataEndpoints
from argparse import ArgumentParser
from base_utils.logger import get_logger
import os, sys, logging

logger = get_logger(__name__, logging.DEBUG)


def parser():
    p = ArgumentParser()
    p.add_argument("--host", default=None, help="Host URL of the Kaapana instance.")
    p.add_argument("--series-file", default="series_uids.txt")
    p.add_argument(
        "--max-time",
        help="The maximum time to wait until all dicoms are available.",
        default=1800,
        type=int,
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="The client secret of the kaapana client in keycloak.",
    )
    return p.parse_args()


def main():
    args = parser()
    host = args.host
    client_secret = args.client_secret or os.environ.get("CLIENT_SECRET", None)
    if not client_secret:
        logger.error(
            "A client secret has to be specified by command line flag or as environment variable CLIENT_SECRET"
        )
        sys.exit(1)
    kaapana = DataEndpoints(host=host, client_secret=client_secret)
    kaapana.check_all_datasets_in_backend()


if __name__ == "__main__":
    main()
