import json
import os
import sys
import time
from pathlib import Path
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/app")

from app.config import settings
from app.utils import all_successful, helm_install, helm_status
from app.helm_helper import get_kube_objects


# create a logger called fastapi so that logs in helm_helper and utils are also visible
logger = logging.getLogger('fastapi')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.debug("set fastapi logger level to debug")

errors_during_preinstalling = False
logger.info('##############################################################################')
logger.info('Preinstalling extensions')
logger.info('##############################################################################')
preinstall_extensions = json.loads(os.environ.get(
    'PREINSTALL_EXTENSIONS', '[]').replace(',]', ']'))

releases_installed = {}
for extension in preinstall_extensions:
    helm_command = 'nothing to say...'
    extension_found = False
    for _ in range(10):
        time.sleep(1)
        extension_path = Path(settings.helm_extensions_cache) / \
            f'{extension["name"]}-{extension["version"]}.tgz'
        if extension_path.is_file():
            extension_found = True
            continue
        else:
            logger.info('Extension not there yet')
    if extension_found is False:
        logger.warning(
            f'Skipping {extension_path}, since we could find the extension in the file system')
        errors_during_preinstalling = True
        continue
    try:
        _, _, _, release_name, _ = helm_install(extension, shell=True, update_state=False)
        releases_installed[release_name] = False
        logger.info(f"Trying to install chart {release_name}")
    except Exception as e:
        logger.error(
            f'Skipping {extension_path}, since we had problems installing the extension {e}')
        errors_during_preinstalling = True
if errors_during_preinstalling is True:
    raise NameError('Problems while preinstallting the extensions!')

for _ in range(7200):
    time.sleep(1)
    for release_name in releases_installed.keys():
        status = helm_status(release_name)
        _, _, ingress_paths, kube_status = get_kube_objects(release_name)
        releases_installed[release_name] = True if all_successful(
            set(kube_status['status'] + [status['STATUS']])) == 'yes' else False
    if sum(list(releases_installed.values())) == len(releases_installed):
        logger.info(f'Sucessfully installed {" ".join(releases_installed.keys())}')
        break

if sum(list(releases_installed.values())) != len(releases_installed):
    raise NameError(
        f'Not all releases were installed successfully {" ".join(releases_installed.keys())}')
