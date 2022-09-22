import os
from platform import release
import secrets
import subprocess
from fastapi import APIRouter, Response, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

import utils
from config import settings
from os.path import basename, dirname, join
import helm_helper
from fastapi.logger import logger


router = APIRouter()
# router = APIRouter(prefix=settings.application_root)
# templates = Jinja2Templates(
#     directory=os.path.abspath(os.path.expanduser('app/templates'))
# )
templates = Jinja2Templates(directory=join(
    dirname(str(__file__)), "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/health-check")
async def health_check():
    # TODO return JSON object
    return Response(f"Kube-Helm api is up and running!", 200)


@router.get("/update-extensions")
async def update_extensions():
    install_error, message = utils.execute_update_extensions()
    if install_error is False:
        return Response(message, 202)
    else:
        return Response(message, 500)


@router.get("/helm-delete-chart")
async def helm_delete_chart(release_name: str, release_version: str = None, helm_command_addons: str = ''):
    # TODO: should be POST
    try:
        success, stdout = utils.helm_delete(
            release_name=release_name, release_version=release_version, helm_command_addons=helm_command_addons)
        if success:
            return Response("Successfully uninstalled {0}".format(release_name), 200)
        else:
            return Response("{0}".format(stdout), 400)
    except subprocess.CalledProcessError as e:
        logger.error("/helm-delete-chart failed: {0}".format(e))
        return Response(f"An internal server error occured!", 500)


@router.post("/helm-install-chart")
async def helm_install_chart(request: Request):
    try:
        payload = await request.json()
        success, stdout, _, release_name = utils.helm_install(
            payload, shell=False)
        if success:
            return Response("Successfully ran helm install for chart '{0}'".format(release_name), 200)
        else:
            return Response("{0}".format(stdout), 400)
    except subprocess.CalledProcessError as e:
        logger.error("/helm-install-chart failed: {0}".format(e))
        return Response(f"An internal server error occured!", 500)


@router.post("/pull-docker-image")
async def pull_docker_image(request: Request):

    try:
        payload = await request.json()
        logger.info(payload)
        release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
        utils.pull_docker_image(release_name, **payload)
        return Response(f"We are trying to download the docker container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 202)
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name)
        logger.error(e)
        return Response(f"We could not download your container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 500)


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
    # TODO: return Response with status code, fix front end accordingly
    return extensions_list


@router.get("/extensions")
async def extensions():
    # cached_extensions = utils.get_extensions_list()
    cached_extensions = helm_helper.get_extensions_list()
    # TODO: return Response with status code, fix front end accordingly
    return cached_extensions


@router.get("/list-helm-charts")
async def add_repo():
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {settings.helm_namespace} ls -o json', stderr=subprocess.STDOUT, shell=True)
        logger.info(resp)
    except subprocess.CalledProcessError as e:
        return Response(f"{e.output}", 500)
    return resp


@router.get("/view-helm-env")
async def view_helm_env():
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} env', stderr=subprocess.STDOUT, shell=True)
        # TODO parse response to json object
        logger.info(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}", 500)
    return Response(str(resp), 200)


@router.get("/view-chart-status")
async def view_chart_status(release_name: str):
    status = utils.helm_status(release_name)
    if status:
        return status
    else:
        return Response(f"Release not found", 404)
