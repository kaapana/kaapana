from app.utils import helm_prefetch_extension_docker, helm_status
from app.config import settings
import time

print('##############################################################################')
print('Prefechting extensions on startup!')
print('##############################################################################')
if settings.offline_mode is False and settings.prefetch_extensions is True:
    try:
        installed_release_names = helm_prefetch_extension_docker()
        print(f"Trying to prefetch all docker container of extensions")
    except:
        raise NameError('Could not prefetch the docker containers, please check the logs!')
    
    for _ in range(7200):
        releases_installed = {release_name: False for release_name in installed_release_names}
        time.sleep(1)
        for release_name in installed_release_names:
            status = helm_status(release_name)
            if not status:
                releases_installed[release_name] = True
        if sum(list(releases_installed.values())) == len(releases_installed):
            print(f'Sucessfully uninstalled all prefetching releases {" ".join(releases_installed.keys())}')
            break
else:
    print(f'Offline mode is set to {settings.offline_mode} and prefetch_extensions is set to {settings.prefetch_extensions}!')
    print("Not prefetching...")

if sum(list(releases_installed.values())) != len(releases_installed):
    raise NameError(f'Not all prefetching releases were uninstalled successfully {" ".join(releases_installed.keys())}')
