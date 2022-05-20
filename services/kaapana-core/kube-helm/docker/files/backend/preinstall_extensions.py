import json
import os
import time
from pathlib import Path
from app.utils import execute_update_extensions, get_manifest_infos, all_successful, cure_invalid_name, helm_install, helm_status, helm_get_manifest
from app.config import settings

errors_during_preinstalling = False
print('##############################################################################')
print('Preinstalling extensions on startup!')
print('##############################################################################')
preinstall_extensions = json.loads(os.environ.get('PREINSTALL_EXTENSIONS', '[]').replace(',]', ']'))

releases_installed = {}
for extension in preinstall_extensions:
    helm_command = 'nothing to say...'
    extension_found = False
    for _ in range(10):
        time.sleep(1)
        extension_path = Path(settings.helm_extensions_cache) / f'{extension["name"]}-{extension["version"]}.tgz'
        if extension_path.is_file():
            extension_found = True
            continue
        else:
            print('Extension not there yet')
    if extension_found is False:
        print(f'Skipping {extension_path}, since we could find the extension in the file system')
        errors_during_preinstalling = True
        continue
    try:
        resp, helm_command, release_name = helm_install(extension, in_background=False)
        releases_installed[release_name] = False
        print(f"Trying to install chart with {helm_command}", resp)
    except Exception as e:
        print(f'Skipping {extension_path}, since we had problems installing the extension')
        print(e)
        errors_during_preinstalling = True
if errors_during_preinstalling is True:
    raise NameError('Problems while preinstallting the extensions!')

for _ in range(7200):
    time.sleep(1)
    for release_name in releases_installed.keys():
        status = helm_status(release_name)
        manifest = helm_get_manifest(release_name)
        kube_status, ingress_paths = get_manifest_infos(manifest)
        releases_installed[release_name] = True if all_successful(set(kube_status['status'] + [status['STATUS']])) == 'yes' else False
    if sum(list(releases_installed.values())) == len(releases_installed):
        print(f'Sucessfully installed {" ".join(releases_installed.keys())}')
        break

if sum(list(releases_installed.values())) != len(releases_installed):
    raise NameError(f'Not all release were installed successfully {" ".join(releases_installed.keys())}')
        