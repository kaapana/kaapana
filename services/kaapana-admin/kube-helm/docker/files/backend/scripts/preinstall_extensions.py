import json
import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/app")

from app.config import settings
from app.helm_helper import execute_shell_command, get_kube_objects, helm_show_chart
from app.utils import helm_install, helm_status
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


def _extract_helm_status(status_obj):
    """Normalize helm_status() return payloads across Helm/client variants."""
    if isinstance(status_obj, dict):
        return str(status_obj.get("STATUS", "")).lower()
    if isinstance(status_obj, list) and len(status_obj) > 0:
        if isinstance(status_obj[0], dict):
            return str(status_obj[0].get("STATUS", "")).lower()
    return ""


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

        # if chart is stuck in 'uninstalling' state, uninstall with --no-hooks
        chart_name = chart["name"]
        chart_status = helm_status(chart_name)
        current_helm_status = _extract_helm_status(chart_status)
        if current_helm_status == "uninstalling":
            # if it is stuck in uninstalling, delete with --no-hooks
            logger.warning(f"{chart_name} stuck in 'uninstalling' status")
            logger.info(f"Deleting {chart_name} with --no-hooks")
            execute_shell_command(
                f"{settings.helm_path} uninstall {chart_name} --no-hooks"
            )
        elif current_helm_status == "deployed":
            logger.info(f"Chart {chart_name} is already installed, skipping")
            continue
        elif current_helm_status.startswith("pending-"):
            logger.info(
                f"Chart {chart_name} is in state '{current_helm_status}', waiting for completion"
            )
            releases_installed[chart_name] = {
                "version": extension["version"],
                "installed": False,
                "is_platform": is_platform,
            }
            continue

        success, install_msg, _, release_name, _ = helm_install(
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
        elif install_msg == "Chart is already installed":
            logger.info(
                f"Chart {release_name} already exists (state: {current_helm_status or 'unknown'}), skipping"
            )
            continue
        else:
            error_message = f"Failed to install chart {release_name}, see error logs"
            logger.error(error_message)
            raise Exception(error_message)

    except Exception as e:
        logger.error(
            f"Skipping {extension_path}, problems installing the extension {e}"
        )
        errors_during_preinstalling = True
        raise e

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
            release_name, helm_namespace=helm_namespace, single_status_for_jobs=True
        )

        if not success:
            logger.warning(
                f"Some Kubernetes objects for release {release_name} are not successful yet"
            )
            continue

        installed = True
        ks = kube_status["status"]
        for i in range(0, len(ks)):
            s = ks[i]
            if type(s) is not str or s.lower() not in [
                "completed",
                "running",
                "deployed",
            ]:
                logger.warning(f"Pod {kube_status['name'][i]} is not successful")
                installed = False
                break

        if installed:
            logger.info(
                f"All Kubernetes objects for release {release_name} are successful"
            )
        else:
            logger.warning(
                f"Some Kubernetes objects for release {release_name} are not successful yet"
            )
        releases_installed[release_name] = {
            "version": release_version,
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
