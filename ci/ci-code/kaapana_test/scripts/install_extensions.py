import argparse
import json
import logging
import sys
import time

from kaapana_test.extensions.utils_extensions import ExtensionEndpoint
from kaapana_test.utils.logger import get_logger


def parser():
    p = argparse.ArgumentParser(
        prog="install_extensions.py",
        usage="Install and uninstall extensions in kaapana via the helm-kube-api",
    )
    p.add_argument(
        "--host", required=True, default=None, help="Host URL of the Kaapana instance."
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="The client secret of the kaapana client in keycloak.",
    )
    p.add_argument("-d", "--delete", action="store_true")
    p.add_argument(
        "--all-extensions", action="store_true", help="Install all available extensions"
    )
    p.add_argument(
        "-e",
        "--extensions",
        nargs="*",
        help="List of extensions to install or delete in the format chart_name:version",
    )
    p.add_argument("--file", help="YAML/JSON file with extension definitions")
    p.add_argument(
        "--json-extension-params",
        help="Path to a json file containing extension specific parameters. The json has to be a dict, where the keys are the chart_names of the extensions and the values are dicts with the extension parameters.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Time in seconds to wait for all extensions to be processed before exiting the program with an error.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parser()
    logger = get_logger(__name__, logging.DEBUG)
    extension_endpoint = ExtensionEndpoint(
        host=args.host,
        client_secret=args.client_secret,
    )

    ##################################################
    ############# COLLECT EXTENSIONS #################
    ##################################################
    # Collect extensions to process
    all_extensions = extension_endpoint.get_all_extensions()
    if args.all_extensions:
        extensions = all_extensions
    else:
        extensions = []
        if args.extensions:
            extensions = ExtensionEndpoint.parse_extension_specs(
                args.extensions, all_extensions
            )

        if args.file:
            extensions = ExtensionEndpoint.load_extensions_from_file(
                args.file, all_extensions
            )

    extension_names = [extension.get("chart_name") for extension in extensions]
    action = "UNINSTALL" if args.delete else "INSTALL"
    logger.info("Requested to %s extensions: %s", action, extension_names)

    processed = []
    succeded = []
    failed = []

    if args.delete:
        processed, failed = extension_endpoint.delete_extensions(extensions)
    else:
        with open(args.json_extension_params) as f:
            extension_params = json.load(f)
        processed, failed = extension_endpoint.install_extensions(extensions, extension_params)

    if failed:
        logger.error(f"Extensions: {failed} failed in kube-helm response.")
        sys.exit(1)

    # Wait for kube-helm to process all requests using timeout and sleep.
    logger.info("Confirm all extension are present in kube-helm")
    start = time.time()
    while abs(time.time() - start) < args.timeout:
        all_processed = True
        for ext in processed:
            extension_installed = extension_endpoint.extension_is_installed(ext)
            if args.delete and extension_installed:
                logger.info(
                    "Extension %s:%s is still installed, waiting for deletion.",
                    ext["chart_name"],
                    ext["latest_version"],
                )
                all_processed = False
            elif not args.delete and not extension_installed:
                logger.info(
                    "Extension %s:%s is not installed, waiting for installation.",
                    ext["chart_name"],
                    ext["latest_version"],
                )
                all_processed = False

        if all_processed:
            logger.info("All extensions are processed successfully.")
            sys.exit(0)

        time.sleep(5)

    logger.error("Timeout reached. Some extensions are not processed successfully.")
    sys.exit(1)
