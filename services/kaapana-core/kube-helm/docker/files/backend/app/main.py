import os
import json
import time
from pathlib import Path
from fastapi import FastAPI

from .routes import router
from fastapi.staticfiles import StaticFiles

from app.utils import execute_update_extensions, helm_install, helm_prefetch_extension_docker
from .config import settings

app = FastAPI(openapi_prefix=os.getenv('APPLICATION_ROOT', ''))

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(
    router,
)

@app.on_event("startup")
def preinstall_extensions():
    print('##############################################################################')
    print('Update extensions on startup!')
    print('##############################################################################')
    install_error = execute_update_extensions()
    if install_error is False:
        print(f"Successfully updated the extensions")
    else:
        raise ValueError(f"We had troubles updating the extensions")

    print('##############################################################################')
    print('Preinstalling extensions on startup!')
    print('##############################################################################')
    preinstall_extensions = json.loads(os.environ.get('PREINSTALL_EXTENSIONS', '[]').replace(',]', ']'))
    for extension in preinstall_extensions:
        helm_command = 'nothing to say...'
        extension_found = False
        for idx in range(10):
            time.sleep(1)
            extension_path = Path(settings.helm_extensions_cache) / f'{extension["name"]}-{extension["version"]}.tgz'
            if extension_path.is_file():
                extension_found = True
                continue
            else:
                print('Extension not there yet')
        if extension_found is False:
            print(f'Skipping {extension_path}, since we could find the extension in the file system')
            continue
        try:
            resp, helm_command = helm_install(extension)
            print(f"Trying to install chart with {helm_command}", resp)
        except Exception as e:
            print(f'Skipping {extension_path}, since we had problems installing the extension')


    print('##############################################################################')
    print('Preinstalling extensions on startup!')
    print('##############################################################################')
    if settings.offline_mode is False and settings.prefetch_extensions is True:
        try:
            helm_prefetch_extension_docker()
            print(f"Trying to prefetch all docker container of extensions")
        except:
            print(f"Could not prefetch the docker containers, please check the logs")
    else:
        print('Offline mode is set to False!')
        print("Not prefetching...")

