import argparse
from yaml import load_all, Loader
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from base_utils.logger import get_logger
from base_utils.utils_extensions import ExtensionEndpoints
import logging, os, sys
import time


def parser():
    p = argparse.ArgumentParser(
        prog="install_extensions.py",
        usage="Install and uninstall extensions in kaapana via the helm-kube-api",
    )

    p.add_argument("extensions", nargs="*")
    p.add_argument("-f", "--file")
    p.add_argument("-d", "--delete", action="store_true")
    p.add_argument("-m", "--multi-installable", action="store_true")
    p.add_argument(
        "--host", required=True, default=None, help="Host URL of the Kaapana instance."
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="The client secret of the kaapana client in keycloak.",
    )
    p.add_argument(
        "--install-all", action="store_true", help="Install all available extensions"
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Time in seconds to wait for all extensions to be processed before exiting the program with an error.",
    )
    p.add_argument("--log-file", default=None, help="Specify the path to a logfile.")
    return p.parse_args()


if __name__ == "__main__":
    args = parser()
    logger = get_logger(__name__, logging.DEBUG, args.log_file)
    client_secret = args.client_secret or os.environ.get("CLIENT_SECRET", None)
    if not client_secret:
        logger.error(
            "A client secret has to be specified by command line flag or as environment variable CLIENT_SECRET"
        )
        sys.exit(1)
    kaapana = ExtensionEndpoints(host=args.host, client_secret=client_secret)

    ##################################################
    ############# COLLECT EXTENSIONS #################
    ##################################################
    if not args.install_all:
        extensions = []
        if (e := args.extensions) and len(e) != 0:
            for input in e:
                app = {}
                app["chart_name"], app["latest_version"] = input.split(":")
                app["release_name"] = app["latest_version"]
            extensions.append(app)
        if file := args.file:
            with open(file) as f:
                extensions += load_all(f, Loader=Loader)
    else:
        extensions = kaapana.get_all_extensions()

    extension_names = [extension.get("chart_name") for extension in extensions]
    proccessed_extensions = []
    names_processed_extensions = []
    not_installed_extensions = []
    already_installed_extensions = []

    action = "UNINSTALL" if args.delete else "INSTALL"
    logger.info(f"Requested to {action} extensions: {extension_names}")

    ##################################################
    ### PERFORM ACTION ON EXTENSIONS #################
    ##################################################
    for extension in extensions:
        name = extension["chart_name"]
        try:
            extension_installed = kaapana.extension_is_installed(extension)
        except:
            logger.warning(
                f"Problem when requesting endpoint kube-helm-api/extensions -> SKIP {action} on {name}."
            )
            continue
        if args.delete:
            if not extension_installed:
                not_installed_extensions.append(name)
            else:
                kaapana.delete_extension(extension)
                proccessed_extensions.append(extension)
                names_processed_extensions.append(name)
        elif extension_installed:
            already_installed_extensions.append(name)
        else:
            kaapana.install_extension(extension)
            proccessed_extensions.append(extension)
            names_processed_extensions.append(name)

    if not_installed_extensions:
        logger.info(
            f"Skip {action} on not installed extensions: {not_installed_extensions}."
        )
    if already_installed_extensions:
        logger.info(
            f"Skip {action} on already installed extensions: {already_installed_extensions}."
        )
    if names_processed_extensions:
        logger.info(f"Perform {action} on extensions: {names_processed_extensions}")

    successfully_proccessed = []
    start_time = time.time()
    timeout = args.timeout

    ##################################################
    ### WAIT FOR THE ACTION TO BE PERFORMED ##########
    ##################################################
    while abs(start_time - time.time()) < timeout and len(
        successfully_proccessed
    ) != len(proccessed_extensions):
        for extension in proccessed_extensions:
            name = extension["chart_name"]
            if name in successfully_proccessed:
                continue
            try:
                extension_installed = kaapana.extension_is_installed(extension)
            except:
                logger.warning(
                    f"Problem when requesting endpoint kube-helm-api/extensions -> Unknown status for {name}."
                )
                continue
            if args.delete:
                if extension_installed:
                    time.sleep(5)
                else:
                    successfully_proccessed.append(name)
            else:
                if not extension_installed:
                    time.sleep(5)
                else:
                    successfully_proccessed.append(name)

    timeout_reached = [
        name
        for name in names_processed_extensions
        if name not in successfully_proccessed
    ]
    if successfully_proccessed:
        logger.info(
            f"Successfully performed action {action} on extensions: {successfully_proccessed}"
        )
    if timeout_reached:
        logger.error(
            f"Timeout reached for action {action} for extensions {timeout_reached}."
        )

    if len(proccessed_extensions) == len(successfully_proccessed):
        sys.exit(0)
    else:
        sys.exit(1)
