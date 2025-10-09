import socket
import time
import os
import requests
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


def check_url(url: str, timeout: int):
    logger.info("Checking URL: {}".format(url))
    try:
        request = requests.get(
            url, timeout=timeout, allow_redirects=False, verify=False
        )
        request.raise_for_status()
        return 0
    except requests.exceptions.ConnectionError:
        logger.warning(f"Connection to {url} could not be established.")
        return 1
    except requests.exceptions.ReadTimeout:
        logger.warning(
            f"Request to {url} timed out. Maybe you have to increase timeout."
        )
        return 1


def check_port(host, port, DELAY, timeout):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        while sock.connect_ex((host, int(port))) != 0:
            logger.info(f"Wait for service {host} and port: {port}!")
            time.sleep(DELAY)
        logger.info(f"Service at {host}:{port} is ready")
        return 0
    except requests.exceptions.ConnectionError:
        logger.warning(f"Connection to {host} could not be established.")
        return 1
    except requests.exceptions.ReadTimeout:
        logger.warning(
            f"Request to {host} timed out. Maybe you have to increase timeout."
        )
        return 1


def main():
    logger.info("Start service-checker ...")
    WAIT = os.getenv("WAIT", None)
    DELAY = int(os.getenv("DELAY", 2))
    TIMEOUT = float(os.getenv("TIMEOUT", 10))
    FILES_AND_FOLDERS_EXISTS = os.getenv("FILES_AND_FOLDERS_EXISTS", None)

    logger.debug(f"{WAIT=}")
    logger.debug(f"{DELAY=}")
    logger.debug(f"{FILES_AND_FOLDERS_EXISTS=}")
    logger.debug(f"{TIMEOUT=}")

    if WAIT == None and FILES_AND_FOLDERS_EXISTS == None:
        logger.error(
            "Environment variables WAIT, FILES_AND_FOLDERS_EXISTS cannot be both undeclared."
        )
        logger.warning("Usage:")
        logger.warning("WAIT='postgres,localhost,5432;...'")
        logger.warning("DELAY=2")
        logger.warning("FILES_AND_FOLDERS_EXISTS='/home/charts/file.json'")
        logger.warning("TIMEOUT=10")
        exit(1)

    if FILES_AND_FOLDERS_EXISTS:
        if FILES_AND_FOLDERS_EXISTS.endswith(";"):
            FILES_AND_FOLDERS_EXISTS = FILES_AND_FOLDERS_EXISTS[:-1]

        for file_or_folder in FILES_AND_FOLDERS_EXISTS.split(";"):
            while not os.path.exists(file_or_folder):
                time.sleep(DELAY)
                logger.info(f"Checking for {file_or_folder}")

    if WAIT:
        if WAIT[len(WAIT) - 1] == ";":
            WAIT = WAIT[: len(WAIT) - 1]

        commands = WAIT.split(";")
        for cmd in commands:
            name = cmd.split(",")[0]
            host = cmd.split(",")[1]
            port = cmd.split(",")[2]
            if len(cmd.split(",")) == 4:
                url = cmd.split(",")[3]
                if port == "443":
                    scheme = "https://"
                else:
                    scheme = "http://"
                url = "{}{}:{}{}".format(scheme, host, port, url)
                while check_url(url, TIMEOUT) != 0:
                    time.sleep(DELAY)
            else:
                while check_port(host, port, DELAY, TIMEOUT) != 0:
                    time.sleep(DELAY)

    logger.info("All tested services available.")


if __name__ == "__main__":
    main()
