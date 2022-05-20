import time
from app.utils import execute_update_extensions, get_manifest_infos, all_successful, cure_invalid_name, helm_status, helm_get_manifest
from app.config import settings

print('##############################################################################')
print('Update extensions on startup!')
print('##############################################################################')
install_error, message = execute_update_extensions()
if install_error is False:
    print(message)
else:
    raise NameError(message)

releases_installed = {}
for idx, kube_helm_collection in enumerate(settings.kube_helm_collections.split(';')[:-1]):
    release_name = cure_invalid_name("-".join(kube_helm_collection.split('/')[-1].split(':')), r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=53)
    releases_installed[release_name] = False

for _ in range(3600):
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