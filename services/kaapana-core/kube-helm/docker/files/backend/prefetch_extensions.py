from app.utils import helm_prefetch_extension_docker
from app.config import settings

print('##############################################################################')
print('Prefechting extensions on startup!')
print('##############################################################################')
if settings.offline_mode is False and settings.prefetch_extensions is True:
    try:
        helm_prefetch_extension_docker()
        print(f"Trying to prefetch all docker container of extensions")
    except:
        print(f"Could not prefetch the docker containers, please check the logs")
else:
    print(f'Offline mode is set to {settings.offline_mode} and prefetch_extensions is set to {settings.prefetch_extensions}!')
    print("Not prefetching...")
