import os
from os.path import basename, dirname, join
import secrets
import subprocess

from fastapi import APIRouter, Response, Request, UploadFile, WebSocket, WebSocketDisconnect
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
        logger.error(f"/file upload failed {msg}")
        return Response(f"File upload failed {msg}", 500)

    return Response(msg, 200)


@router.post("/file_chunks_init")
async def file_chunks_init(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"in file_chunks_init, {payload=}")
        req_keys = ("name", "fileSize",
                    "chunkSize", "index", "endIndex")
        if not all(k in req_keys for k in payload.keys()):
            raise AssertionError(
                f"All following keys are required: {req_keys}")
        fpath, msg = file_handler.init_file_chunks(
            fname=payload["name"],
            fsize=payload["fileSize"],
            chunk_size=payload["chunkSize"],
            index=payload["index"],
            endindex=payload["endIndex"]
        )
        if not fpath:
            logger.error(msg)
            return Response(f"file upload init failed {msg}", 500)
        return Response(msg, 200)
    except Exception as e:
        logger.error(f"/file_chunks_init failed {str(e)}")
        return Response(f"File upload init failed {str(e)}", 500)


@router.post("/file_chunks")
async def upload_file_chunks(file: UploadFile):
    try:
        logger.debug(
            f"in upload_file_chunks {file.filename}, {file.content_type}")
        content = await file.read()
        next_index = file_handler.add_file_chunks(content)
        return Response(str(next_index), 200)
    except Exception as e:
        msg = str(e)
        logger.error(f"/file_chunks failed: {msg}")
        return Response(f"File upload failed", 500)


# @router.websocket("/file_chunks/{client_id}")
# async def ws_upload_file_chunks(ws: WebSocket, client_id: int):
#     logger.info(f"in function upload_file_chunks with {client_id=}")
#     try:
#         await ws.accept()
#         file_info = await ws.receive_json()
#         logger.info(f"file info received in websocket: {file_info}")
#         fname = file_info["name"]
#         fsize = file_info["fileSize"]
#         chunk_size = file_info["chunkSize"]

#         fpath, msg = await file_handler.ws_add_file_chunks(ws, fname, fsize, chunk_size)

#         if fpath == "":
#             logger.error(msg)
#             return Response(msg, 500)

#     except WebSocketDisconnect:
#         logger.warning(f"WebSocket disconnected {client_id=}")
#     except Exception as e:
#         logger.error(f"upload file failed: {e}")


@router.get("/import-container")
async def import_container(filename: str):
    try:
        logger.info(f"/import-container called with {filename}")
        assert filename != "", "Required key 'filename' can not be empty"
        res, msg = file_handler.run_containerd_import(filename)
        logger.debug(f"returned {res=}, {msg=}")
        if not res:
            logger.error(f"/import-container failed {msg}")
            return Response(f"Container import failed {msg}", 500)
        return Response(msg, 200)
    except AssertionError as e:
        logger.error(f"/import-container failed: {str(e)}")
        return Response(f"Container import failed, bad request {str(e)}", 400)
    except Exception as e:
        logger.error(f"/import-container failed: {str(e)}")
        return Response(f"Container import failed, bad request {str(e)}", 500)

@router.get("/health-check")
async def health_check():
    return Response(f"Kube-Helm api is up and running!", 200)


@router.get("/update-extensions")
async def update_extensions():
    install_error, msg = utils.execute_update_extensions()
    if install_error is False:
        return Response(msg, 202)
    else:
        logger.error(f"/update-extensions failed {msg}")
        return Response(f"Extensions update failed {msg}", 500)


@router.post("/helm-delete-chart")
async def helm_delete_chart(request: Request):
    try:
        payload = await request.json()
        logger.info(f"/helm-delete-chart called with {payload=}")
        assert "release_name" in payload, "Required key 'release_name' not found in payload"
        release_version = None
        helm_command_addons = ''
        helm_namespace = settings.helm_namespace
        multiinstallable = False
        if "release_version" in payload:
            release_version = payload["release_version"]
        if "helm_command_addons" in payload:
            helm_command_addons = payload["helm_command_addons"]
        if "helm_namespace" in payload:
            helm_namespace = payload["helm_namespace"]
        if ("multiinstallable" in payload) and payload["multiinstallable"].lower() in ["true", "yes"]:
            multiinstallable = True
        success, stdout = utils.helm_delete(
            release_name=payload["release_name"],
            release_version=release_version,
            helm_namespace=helm_namespace,
            helm_command_addons=helm_command_addons,
            multiinstallable=multiinstallable
        )
        if success:
            return Response(f"Successfully ran uninstall command for {payload['release_name']}", 200)
        else:
            return Response(f"{stdout}", 400)
    except AssertionError as e:
        logger.error(f"/helm-delete-chart failed: {str(e)}")
        return Response(f"Chart uninstall failed, bad request {str(e)}", 400)
    except Exception as e:
        logger.error("/helm-delete-chart failed: {0}".format(e))
        return Response(f"Chart uninstall failed {str(e)}", 500)


@router.post("/helm-install-chart")
async def helm_install_chart(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"/helm-install-chart called with {payload=}")
        assert "name" in payload, "Required key 'name' not found in payload"
        assert "version" in payload, "Required key 'version' not found in payload"
        platforms = False
        cmd_addons=""
        blocking=False
        if ("platforms" in payload) and (str(payload["platforms"]).lower() == "true"):
            platforms = True
            cmd_addons = "--create-namespace"
        if ("blocking" in payload) and (str(payload["blocking"]).lower() == "true"):
            blocking = True
        success, stdout, _, _, cmd = utils.helm_install(
            payload, shell=True, blocking=blocking, platforms=platforms, helm_command_addons=cmd_addons)
        if success:
            if blocking:
                return Response(f"Successfully installed: {stdout}", 200)
            else:
                return Response(f"Successfully ran helm install command {cmd}", 200)
        else:
            return Response(f"Chart install command failed {stdout}", 500)
    except AssertionError as e:
        logger.error(f"/helm-install-chart failed: {str(e)}")
        return Response(f"Chart install failed, bad request {str(e)}", 400)
    except Exception as e:
        logger.error("/helm-install-chart failed: {0}".format(e))
        return Response(f"Chart install failed {str(e)}", 500)


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
        return Response(f"Unable to download container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 500)
    except Exception as e:
        logger.error("/pull-docker-image failed: {0}".format(e))
        return Response("Pulling docker image failed {0}".format(e), 400)

@router.get("/pending-applications")
async def pending_applications():
    try:
        extensions_list = []
        for chart in utils.helm_ls(release_filter='kaapanaint'):
            _, _, ingress_paths, kube_status = helm_helper.get_kube_objects(
                chart["name"])
            extension = {
                'releaseName': chart['name'],
                'links': ingress_paths,
                'helmStatus': chart['status'].capitalize(),
                'successful': utils.all_successful(set(kube_status['status'] + [chart['status']])),
                'kubeStatus': ", ".join(kube_status['status'])
            }
            extensions_list.append(extension)

        # TODO: return Response with status code, fix front end accordingly
        return extensions_list

    except subprocess.CalledProcessError as e:
        logger.error("/pending-applications failed {0}".format(e))
        return Response("Internal server error!", 500)
    except Exception as e:
        logger.error(f"/pending-applications failed: {e}".format(e))
        return Response(f"Pending applications failed {e}".format(e), 400)


@router.get("/extensions")
async def extensions():
    # TODO: return Response with status code, fix front end accordingly
    try:
        cached_extensions = helm_helper.get_extensions_list()
        
        return cached_extensions
    
    except Exception as e:
        logger.error(f"/extensions FAILED {e}")
        return Response(f"Failed to get extensions", 500)
    

@router.get("/platforms")
async def get_platforms():
    try:
        platforms = helm_helper.get_extensions_list(platforms=True)

        return platforms
    
    except Exception as e:
        logger.error(f"/platforms FAILED {e}")
        return Response(f"Failed to get platforms", 500)

@router.get("/view-chart-status")
async def view_chart_status(release_name: str):
    status = utils.helm_status(release_name)
    if status:
        return status
    else:
        return Response(f"Release not found", 404)
