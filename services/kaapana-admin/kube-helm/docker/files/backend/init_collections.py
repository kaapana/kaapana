import os
import sys
import time
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/app")

from app.config import settings
from app.utils import execute_update_extensions, all_successful, cure_invalid_name, helm_status
from app.helm_helper import get_kube_objects

logger = logging.getLogger('fastapi')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.debug("set fastapi logger level to debug")

logger.info('##############################################################################')
logger.info('Update extensions on startup!')
logger.info('##############################################################################')
install_error, message = execute_update_extensions()
if install_error is False:
    logger.info("Update extensions successful: %s", message)
else:
    logger.error("Update extensions failed: %s", message)
    raise NameError(message)

releases_installed = {}
for idx, kube_helm_collection in enumerate(settings.kaapana_collections.split(';')[:-1]):
    release_name = cure_invalid_name("-".join(kube_helm_collection.split('/')[-1].split(':')), r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=53)
    releases_installed[release_name] = False

for _ in range(3600):
    time.sleep(1)
    for release_name in releases_installed.keys():
        status = helm_status(release_name)
        _, _, ingress_paths, kube_status = get_kube_objects(release_name)
        releases_installed[release_name] = True if all_successful(set(kube_status['status'] + [status['STATUS']])) == 'yes' else False
    if sum(list(releases_installed.values())) == len(releases_installed):
        logger.info(f'Sucessfully installed {" ".join(releases_installed.keys())}')
        break

if sum(list(releases_installed.values())) != len(releases_installed):
    raise NameError(f'Not all releases were installed successfully {" ".join(releases_installed.keys())}')
