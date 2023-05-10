import os
import sys
import time
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/app")

from app.utils import helm_prefetch_extension_docker, helm_status
from app.config import settings

logger = logging.getLogger("fastapi")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.debug("set fastapi logger level to debug")

logger.info(
    "##############################################################################"
)
logger.info("Prefechting extensions on startup!")
logger.info(
    "##############################################################################"
)
if settings.offline_mode is False and settings.prefetch_extensions is True:
    try:
        installed_release_names = helm_prefetch_extension_docker()
        logger.info(f"Trying to prefetch all docker container of extensions")
    except Exception as e:
        logger.error(f"Prefetch failed {e}")
        raise NameError(
            "Could not prefetch the docker containers, please check the logs!"
        )

    for _ in range(7200):
        releases_installed = {
            release_name: False for release_name in installed_release_names
        }
        time.sleep(1)
        for release_name in installed_release_names:
            status = helm_status(release_name)
            if not status:
                releases_installed[release_name] = True
        if sum(list(releases_installed.values())) == len(releases_installed):
            logger.info(
                f'Sucessfully uninstalled all prefetching releases {" ".join(releases_installed.keys())}'
            )
            break
    if sum(list(releases_installed.values())) != len(releases_installed):
        raise NameError(
            f'Not all prefetching releases were uninstalled successfully {" ".join(releases_installed.keys())}'
        )

else:
    logger.info(
        f"Offline mode is set to {settings.offline_mode} and prefetch_extensions is set to {settings.prefetch_extensions}!"
    )
    logger.info("Not prefetching...")
