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
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.debug("set fastapi logger level to debug")

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
            extension, shell=True, update_state=False, blocking=True, platforms=is_platform
        )
        releases_installed[release_name] = {
            "version": extension["version"],
            "installed": False,
        }
        if success:
            logger.info(f"Chart {release_name} successfully installed")
        else:
            logger.info(f"Failed to install chart {release_name}, see error logs")

    except Exception as e:
        logger.error(
            f"Skipping {extension_path}, problems installing the extension {e}"
        )
        errors_during_preinstalling = True

if errors_during_preinstalling is True:
    raise NameError("Problems while preinstallting the extensions!")

# post-install checks for helm and kube status
for _ in range(3600):
    time.sleep(1)
    for release_name in releases_installed.keys():
        release_version = releases_installed[release_name]["version"]
        status = helm_status(release_name)
        _, _, _, kube_status = get_kube_objects(release_name)
        chart = helm_show_chart(release_name, release_version)
        is_platform = False
        if "keywords" in chart and "kaapanaplatform" in chart["keywords"]:
            is_platform = True
        installed = False
        logger.debug(f"{is_platform=}")
        if is_platform:
            installed = (
                True
                if all_successful(
                    set(kube_status["status"] + [i["STATUS"] for i in status])
                )
                == "yes"
                else False
            )
        else:
            installed = (
                True
                if all_successful(set(kube_status["status"] + [status["STATUS"]]))
                == "yes"
                else False
            )
        releases_installed[release_name] = {
            "version": extension["version"],
            "installed": installed,
        }
    s = sum([i["installed"] for i in list(releases_installed.values())])
    if s == len(releases_installed):
        logger.info(f'Sucessfully installed {" ".join(releases_installed.keys())}')
        break

s = sum([i["installed"] for i in list(releases_installed.values())])
if s != len(releases_installed):
    raise NameError(
        f'Not all releases were installed successfully {" ".join(releases_installed.keys())}'
    )

logger.info(f"preinstall extensions completed {releases_installed=}")
