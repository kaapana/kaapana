import os
from os.path import basename, dirname, join
import secrets
import subprocess

from fastapi import APIRouter, Response, Request, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.logger import logger
import aiofiles

from config import settings
import helm_helper
import utils
import file_handler

# TODO: add endpoint for /helm-delete-file
# TODO: add dependency injection

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


@router.post("/file")
async def upload_file(file: UploadFile):
    logger.info(f"chart file {file.filename}")
    content = await file.read()
    res, msg = file_handler.add_file(file, content)
    if not res:
        logger.error(msg)
        return Response(msg, 500)

    return Response(msg, 200)


@router.post("/file_chunks")
async def upload_file_chunk(file: UploadFile):
    logger.info(f"container file {file.filename}")
    res, msg = await file_handler.add_file_chunks(file)

    if not res:
        logger.error(msg)
        return Response(msg, 500)

    return Response(msg, 200)


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


@router.post("/helm-delete-chart")
async def helm_delete_chart(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"/helm-delete-chart called with {payload=}")
        success, stdout = utils.helm_delete(
            release_name=payload["release_name"],
            release_version=payload["release_version"],
            helm_command_addons=payload["helm_command_addons"]
        )
        if success:
            return Response("Successfully uninstalled {0}".format(payload["release_name"]), 200)
        else:
            return Response("{0}".format(stdout), 400)
    except subprocess.CalledProcessError as e:
        logger.error("/helm-delete-chart failed: {0}".format(e))
        return Response(f"An internal server error occured!", 500)


@router.post("/helm-install-chart")
async def helm_install_chart(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"/helm-install-chart called with {payload=}")
        success, stdout, _, _, cmd = utils.helm_install(
            payload, shell=True, blocking=False)
        if success:
            return Response("Successfully ran helm install, command {0}".format(cmd), 200)
        else:
            return Response("{0}".format(stdout), 400)
    except subprocess.CalledProcessError as e:
        logger.error("/helm-install-chart failed: {0}".format(e))
        return Response(f"An internal server error occured!", 500)


@router.post("/pull-docker-image")
async def pull_docker_image(request: Request):
    """
    Runs helm install command in the background
    """
    try:
        payload = await request.json()
        logger.info(f"/pull-docker-image called {payload=}")
        release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
        utils.pull_docker_image(release_name, **payload)
        return Response(f"Trying to download the docker container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 202)
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name)
        logger.error(e)
        return Response(f"We could not download your container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 500)


@router.get("/pending-applications")
async def pending_applications():
    try:
        extensions_list = []
        for chart in utils.helm_ls(release_filter='kaapanaint'):
            _, _, ingress_paths, kube_status = helm_helper.get_kube_objects(chart["name"])
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
def extensions():
    # cached_extensions = utils.get_extensions_list()
    cached_extensions = helm_helper.get_extensions_list()
    # TODO: return Response with status code, fix front end accordingly
    return cached_extensions


@router.get("/view-chart-status")
def view_chart_status(release_name: str):
    status = utils.helm_status(release_name)
    if status:
        return status
    else:
        return Response(f"Release not found", 404)
