import os
import secrets
import subprocess
import yaml

from fastapi import APIRouter, Response, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app import utils
from .config import settings


router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.abspath(os.path.expanduser('app/templates'))
)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/health-check")
async def health_check():
    # TODO return JSON object
    return Response(f"Kube-Helm api is up and running!", 200)


@router.get("/update-extensions")
async def update_extensions():

    install_error = utils.execute_update_extensions()
    if install_error is False:
        return Response(f"Successfully updated the extensions", 202)
    else:
        return Response(f"We had troubles updating the extensions", 500)


@router.get("/helm-delete-chart")
async def helm_delete_chart(release_name: str, release_version: str = None):
    try:
        utils.helm_delete(release_name=release_name, release_version=release_version)
        return {"message": "Successfully uninstalled", "status": "200"}
    except subprocess.CalledProcessError as e:
        return Response(f"We could not find the release you are trying to delete!", 500)


@router.post("/helm-install-chart")
async def helm_add_custom_chart(request: Request):
    # TODO check if chart already exists and return https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/409
    helm_command = 'nothing to say...'
    try:
        payload = await request.json()
        resp, helm_command = utils.helm_install(payload)
        return Response(f"Trying to install chart with {helm_command}", 200)
    except:
        return Response(f"A helm command error occured while executing {helm_command}!", 500)


@router.post("/pull-docker-image")
async def pull_docker_image(request: Request):

    try:
        payload = await request.json()
        print(payload)
        release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
        utils.pull_docker_image(release_name, **payload)
        return Response(f"We are trying to download the docker container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 202)
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name)
        print(e)
        return Response(f"We could not download your container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 500)


@router.get("/prefetch-extension-docker")
async def prefetch_extension_docker():
    print('prefechting')
    if settings.offline_mode is False:
        try:
            utils.helm_prefetch_extension_docker()
            return Response(f"Trying to prefetch all docker container of extensions", 200)
        except:
            return Response(f"An error occured!", 500)
    else:
        print('Offline mode is set to False!')
        return Response(f"We will not prefetch the extensions since the platform was installed with OFFLINE_MODE set to true!", 200)


@router.get("/pending-applications")
async def pending_applications():
    try:
        extensions_list = []
        for chart in utils.helm_ls(release_filter='kaapanaint'):
            manifest = utils.helm_get_manifest(chart['name'])
            kube_status, ingress_paths = utils.get_manifest_infos(manifest)
            extension = {
                'releaseName': chart['name'],
                'links': ingress_paths,
                'helmStatus': chart['status'].capitalize(),
                'successful': utils.all_successful(set(kube_status['status'] + [chart['status']])),
                'kubeStatus': ", ".join(kube_status['status'])
            }
            extensions_list.append(extension)

    except subprocess.CalledProcessError as e:
        return Response(f"{e.output}", 500)
    return extensions_list


@router.get("/extensions")
async def extensions():
    return utils.extensions_list_cached


@router.get("/list-helm-charts")
async def add_repo():
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {settings.helm_namespace} ls -o json', stderr=subprocess.STDOUT, shell=True)
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(f"{e.output}", 500)
    return resp


@router.get("/view-helm-env")
async def view_helm_env():
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} env', stderr=subprocess.STDOUT, shell=True)
        # TODO parse response to json object
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}", 500)
    return {"message": str(resp), "status": "200"}


@router.get("/view-chart-status")
async def view_chart_status(release_name: str):
    status = utils.helm_status(release_name)
    if status:
        return status
    else:
        return Response(f"Release not found", 404)
