import json
import os
import sys
import time
from pathlib import Path
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/app")

from app.config import settings
from app.utils import all_successful, helm_install, helm_status
from app.helm_helper import get_kube_objects, helm_show_chart


logger = logging.getLogger("fastapi")
# set log level
log_level = settings.log_level.upper()
if log_level == "DEBUG":
    log_level = logging.DEBUG
elif log_level == "INFO":
    log_level = logging.INFO
elif log_level == "WARNING":
    log_level = logging.WARNING
elif log_level == "ERROR":
    log_level = logging.ERROR
elif log_level == "CRITICAL":
    log_level = logging.CRITICAL
else:
    logging.error(
        f"Unknown log-level: {settings.log_level} -> Setting log-level to 'INFO'"
    )
    log_level = logging.INFO

logger.setLevel(log_level)

ch = logging.StreamHandler()
ch.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.debug(f"set fastapi logger level to {log_level}")

# init
errors_during_preinstalling = False
logger.info("Preinstalling extensions")
preinstall_extensions = json.loads(
    os.environ.get("PREINSTALL_EXTENSIONS", "[]").replace(",]", "]")
)
releases_installed = {}

# check if tgz file exists in the folder
for extension in preinstall_extensions:
    extension_found = False
    for _ in range(10):
        time.sleep(1)
        extension_path = (
            Path(settings.helm_extensions_cache)
            / f'{extension["name"]}-{extension["version"]}.tgz'
        )
        if extension_path.is_file():
            extension_found = True
            continue
        else:
            logger.info("Extension not there yet")

    # if the file does not exist
    if extension_found is False:
        logger.warning(
            f"Skipping {extension_path}, since we could find the extension in the file system"
        )
        errors_during_preinstalling = True
        continue

    # install
    try:
        chart = helm_show_chart(extension["name"], extension["version"])
        is_platform = False
        if "keywords" in chart and "kaapanaplatform" in chart["keywords"]:
            is_platform = True
        success, _, _, release_name, _ = helm_install(
            extension,
            shell=True,
            update_state=False,
            blocking=True,
            platforms=is_platform,
        )
        releases_installed[release_name] = {
            "version": extension["version"],
            "installed": False,
            "is_platform": is_platform,
        }
        if success:
            logger.info(f"Chart {release_name} successfully installed")
        else:
            error_message = f"Failed to install chart {release_name}, see error logs"
            logger.error(error_message)
            raise Exception(error_message)

    except Exception as e:
        logger.error(
            f"Skipping {extension_path}, problems installing the extension {e}"
        )
        errors_during_preinstalling = True
        # stop installing other extensions if any platform installation fails
        if is_platform:
            break

if errors_during_preinstalling is True:
    raise NameError("Problems while preinstalling extensions!")

# post-install checks for helm and kube status
for _ in range(1800):
    time.sleep(1)
    for release_name in releases_installed.keys():
        release_version = releases_installed[release_name]["version"]
        is_platform = releases_installed[release_name]["is_platform"]

        helm_namespace = settings.helm_namespace
        if is_platform:
            helm_namespace = "default"
        status = helm_status(release_name, helm_namespace=helm_namespace)
        success, _, _, kube_status = get_kube_objects(
            release_name, helm_namespace=helm_namespace
        )

        if not success:
            logger.warning(
                f"Some Kubernetes objects for release {release_name} are not successful yet"
            )
            continue

        installed = (
            True
            if all_successful(set(kube_status["status"] + [status["STATUS"]])) == "yes"
            else False
        )

        if installed:
            logger.info(
                f"All Kubernetes objects for release {release_name} are successful"
            )
        else:
            logger.warning(
                f"Some Kubernetes objects for release {release_name} are not successful yet"
            )
        releases_installed[release_name] = {
            "version": extension["version"],
            "installed": installed,
            "is_platform": is_platform,
        }

    s = sum([i["installed"] for i in list(releases_installed.values())])
    if s == len(releases_installed):
        logger.info(f'Sucessfully installed {" ".join(releases_installed.keys())}')
        break

s = sum([i["installed"] for i in list(releases_installed.values())])
if s != len(releases_installed):
    logger.warning(
        f'Not all releases were installed successfully {" ".join(releases_installed.keys())}'
    )

logger.info(f"preinstall extensions completed {releases_installed=}")
