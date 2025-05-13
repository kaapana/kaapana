import base64
import json
import logging
import secrets
import subprocess
from os.path import dirname, join
from typing import Optional, List

import file_handler
import helm_helper
import schemas
import httpx
from config import settings
from fastapi import APIRouter, HTTPException, Query, Request, Response, UploadFile 
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from logger import get_logger

import utils

# TODO: add endpoint for /helm-delete-file
# TODO: add dependency injection

router = APIRouter()
# router = APIRouter(prefix=settings.application_root)
# templates = Jinja2Templates(
#     directory=os.path.abspath(os.path.expanduser('app/templates'))
# )
templates = Jinja2Templates(directory=join(dirname(str(__file__)), "templates"))

logger = get_logger(__name__)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/filepond-upload")
async def post_filepond_upload(request: Request):
    try:
        form = await request.form()
        logger.info(f"POST filepond-upload called, req form {form}")
        patch = file_handler.filepond_init_upload(form)

    except Exception as e:
        logger.error(f"/file upload failed {e}", exc_info=True)
        return Response("Filepond Upload Initialization failed", status_code=500)

    return Response(content=patch, status_code=200)


@router.patch("/filepond-upload")
async def patch_filepond_upload(request: Request, patch: str):
    logger.debug(f"PATCH filepond-upload called, {request=} {patch=}")
    ulength = request.headers.get("upload-length", None)
    uname = request.headers.get("upload-name", None)
    res, success = await file_handler.filepond_upload_stream(
        request, patch, ulength, uname
    )
    if success and res == "":
        return Response(patch, 200)
    elif success and res != "":
        return Response(f"{res} uploaded succesfully", 200)
    elif not success:
        return Response(f"Filepond upload failed: {res}", 500)
    else:
        return Response(f"Filepond upload failed: Internal Error", 500)


@router.head("/filepond-upload")
def head_filepond_upload(request: Request, patch: str):
    logger.info(f"HEAD filepond-upload called, {request=} {patch=}")
    ulength = request.headers.get("upload-length", None)
    try:
        offset = file_handler.filepond_get_offset(patch, ulength)
        return Response(str(offset), 200)
    except Exception as e:
        logger.error(e, exc_info=True)
        return Response(f"HEAD /filepond-upload failed {e}", 500)


@router.delete("/filepond-upload")
async def delete_filepond_upload(request: Request):
    logger.info(f"DELETE filepond-upload called, {request=}")
    body = await request.body()
    patch = body.decode("utf-8")
    fname = file_handler.filepond_delete(patch)
    if fname != "":
        return Response(f"Deleted {fname} succesfully.", 200)
    else:
        return Response(
            "Only removing the file in frontend, the file in the target location was already successfully uploaded",
        )


@router.post("/file")
async def upload_file(file: UploadFile):
    logger.info(f"chart file {file.filename}")
    content = await file.read()
    platforms = False
    if file.filename.startswith("/platform/"):
        platforms = True
    res, msg = file_handler.add_file(file, content, platforms)
    if not res:
        logger.error(f"/file upload failed {msg}")
        return Response(f"File upload failed {msg}", 500)

    return Response(msg, 200)


@router.post("/file_chunks_init")
async def file_chunks_init(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"in file_chunks_init, {payload=}")
        req_keys = ("name", "fileSize", "chunkSize", "index", "endIndex")
        if not all(k in payload.keys() for k in req_keys):
            raise AssertionError(f"All following keys are required: {req_keys}")
        platforms = False
        if "platforms" in payload:
            platforms = payload["platforms"]
        fpath, msg = file_handler.init_file_chunks(
            fname=payload["name"],
            fsize=payload["fileSize"],
            chunk_size=payload["chunkSize"],
            index=payload["index"],
            endindex=payload["endIndex"],
            platforms=platforms,
        )
        if not fpath:
            logger.error(msg)
            return Response(f"file upload init failed {msg}", 500)
        return Response(msg, 200)
    except Exception as e:
        logger.error(f"/file_chunks_init failed {e}", exc_info=True)
        return Response(f"File upload init failed {e}", 500)


@router.post("/file_chunks")
async def upload_file_chunks(file: UploadFile):
    try:
        logger.debug(f"in upload_file_chunks {file.filename}, {file.content_type}")
        content = await file.read()
        next_index = file_handler.add_file_chunks(content)
        return Response(str(next_index), 200)
    except Exception as e:
        logger.error(f"/file_chunks failed: {e}", exc_info=True)
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
async def import_container(filename: str, platforms: Optional[bool] = False):
    try:
        logger.info(f"/import-container called with {filename=}, {platforms=}")
        assert filename != "", "Required key 'filename' can not be empty"
        res, msg = await file_handler.run_containerd_import(
            filename, platforms=platforms
        )
        logger.debug(f"returned {res=}, {msg=}")
        if not res:
            logger.error(f"/import-container failed {msg}")
            return Response(f"Container import failed {msg}", 500)
        logger.info(f"Successfully imported {filename}")
        return Response(msg, 200)
    except AssertionError as e:
        logger.error(f"/import-container failed: {e}", exc_info=True)
        raise HTTPException(400, f"Container import failed, bad request {str(e)}")
    except Exception as e:
        logger.error(f"/import-container failed: {e}", exc_info=True)
        raise HTTPException(500, f"Container import failed, bad request {str(e)}")


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
        assert (
            "release_name" in payload
        ), "Required key 'release_name' not found in payload"
        release_version = None
        helm_command_addons = ""
        helm_namespace = settings.helm_namespace
        multiinstallable = False
        platforms = False
        if "release_version" in payload:
            release_version = payload["release_version"]
        if "helm_command_addons" in payload:
            helm_command_addons = payload["helm_command_addons"]
        if "helm_namespace" in payload:
            helm_namespace = payload["helm_namespace"]
        if ("multiinstallable" in payload) and payload["multiinstallable"].lower() in [
            "true",
            "yes",
        ]:
            multiinstallable = True
        if "platforms" in payload:
            platforms = payload["platforms"]
        success, stdout = utils.helm_delete(
            release_name=payload["release_name"],
            release_version=release_version,
            helm_namespace=helm_namespace,
            helm_command_addons=helm_command_addons,
            multiinstallable=multiinstallable,
            platforms=platforms,
        )
        if success:
            return Response(f"Started uninstalling {payload['release_name']}", 200)
        else:
            return Response(f"Chart uninstall command failed{stdout}", 400)
    except AssertionError as e:
        logger.error(f"/helm-delete-chart failed: {str(e)}", exc_info=True)
        return Response(f"Chart uninstall failed, bad request {str(e)}", 400)
    except Exception as e:
        logger.error(f"/helm-delete-chart failed: {e}", exc_info=True)
        return Response(f"Chart uninstall failed {str(e)}", 500)


@router.post("/helm-install-chart")
async def helm_install_chart(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"/helm-install-chart called with {payload=}")
        assert "name" in payload, "Required key 'name' not found in payload"
        assert "version" in payload, "Required key 'version' not found in payload"
        platforms = False
        cmd_addons = ""
        blocking = False
        if ("platforms" in payload) and (str(payload["platforms"]).lower() == "true"):
            platforms = True
            cmd_addons = "--create-namespace"
        if ("blocking" in payload) and (str(payload["blocking"]).lower() == "true"):
            blocking = True
        if (
            keywords := payload.get("keywords")
        ) and "kaapanamultiinstallable" in keywords:
            project_form = json.loads(request.headers.get("Project"))
            payload["extension_params"] = payload.get("extension_params", {})
            payload["extension_params"]["project_id"] = project_form.get("id")
            payload["extension_params"]["project_name"] = project_form.get("name")

        not_installed, _, keywords, release_name, cmd = utils.helm_install(
            payload,
            shell=True,
            blocking=blocking,
            platforms=platforms,
            helm_command_addons=cmd_addons,
            execute_cmd=False,
        )
        if not not_installed:
            return Response(f"Chart is already installed {release_name}", 204)
        success, stdout = await utils.helm_install_cmd_run_async(
            release_name, payload["version"], cmd, keywords
        )
        logger.debug(f"await ended {success=} {stdout=}")
        if success:
            return Response(f"Successfully installed: {release_name}", 200)
        else:
            return Response(f"Chart install command failed for {release_name}", 500)
    except AssertionError as e:
        logger.error(f"/helm-install-chart failed: {str(e)}", exc_info=True)
        return Response(f"Chart install failed, bad request {str(e)}", 400)
    except Exception as e:
        logger.error(f"/helm-install-chart failed: {e}", exc_info=True)
        return Response(f"Chart install failed {str(e)}", 500)


@router.post("/pull-docker-image")
async def pull_docker_image(request: Request):
    """
    Runs helm install command in the background
    """
    try:
        payload = await request.json()
        logger.info(f"/pull-docker-image called {payload=}")
        release_name = f"pull-docker-chart-{secrets.token_hex(10)}"
        utils.pull_docker_image(release_name, **payload)
        return Response(
            f"Trying to download the docker container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}",
            202,
        )
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name)
        logger.error(e, exc_info=True)
        return Response(
            f"Unable to download container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}",
            500,
        )
    except Exception as e:
        logger.error(f"/pull-docker-image failed: {e}", exc_info=True)
        return Response(f"Pulling docker image failed {e}", 400)


@router.post("/complete-active-application")
async def complete_active_application(request: Request):
    try:
        payload = await request.json()
        logger.info(f"/complete-active-application called with {payload=}")

        release_name = payload.get("release_name")
        if not release_name:
            return Response(
                "Payload does not have mandatory key: 'release_name'", status_code=400
            )
        # check if the deployed release contains label: kaapanaint
        if not utils.helm_ls(
            release_filter=release_name, label_filter="kaapana.ai/kaapanaint=True"
        ):
            logger.error(
                f"No deployed releases found with name: {release_name} and label: kaapana.ai/kaapanaint=True"
            )
            return HTTPException(
                f"Failed to complete active application: release {release_name} does not have correct annotations",
                status_code=500,
            )

        # delete chart
        success, stdout = utils.helm_delete(release_name=release_name)
        if success:
            logger.info(f"Successfully completed active application {release_name}")
            return Response(
                f"Completed active application: {release_name}", status_code=200
            )
        else:
            logger.error(f"Helm chart deletion failed for {release_name}: {stdout}")
            return Response(
                f"Failed to complete active application: {stdout}", status_code=500
            )

    except Exception as e:
        logger.error(f"/complete-active-application failed: {str(e)}", exc_info=True)
        return Response(f"Internal server error: {str(e)}", status_code=500)


@router.get("/active-applications", response_model=List[schemas.ActiveApplication])
async def get_active_applications() -> List[schemas.ActiveApplication]:
    """
    Returns a list of all active applications (i.e. applications that have an ingress) that match the annotation filter:
        `'kaapana.ai/type' == 'application'` OR `'kaapana.ai/type' == 'triggered'`
    """
    try:
        ingress_annotation_filters = [
            {"kaapana.ai/type": "application"},
            {"kaapana.ai/type": "triggered"},
        ]
        # get all ingress objects
        active_apps = utils.get_active_apps_from_ingresses(ingress_annotation_filters)
        logger.info(
            f"Found {active_apps=} ingresses with filter {ingress_annotation_filters}"
        )
        if not active_apps:
            logger.warning(
                f"No application ingresses found with filter {ingress_annotation_filters}"
            )
            return []

        # add "ready" status to the found ingress objects
        for active_app in active_apps:
            # get the release name of the chart from ingress
            release_name = active_app["release_name"]
            # get all k8s objects of the chart and the ready status
            _, ready, _, _ = helm_helper.get_kube_objects(release_name)
            # find the deployed chart inside the extension object
            active_app["ready"] = ready

        return active_apps
    except Exception as e:
        logger.error(f"/active-applications failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Getting active applications failed: {str(e)}"
        )


@router.get("/extensions")
async def extensions():
    # TODO: return Response with status code, fix front end accordingly
    try:
        cached_extensions = helm_helper.get_extensions_list()

        return cached_extensions

    except Exception as e:
        logger.error(f"/extensions FAILED", exc_info=True)
        return Response(f"Failed to get extensions", 500)


@router.get("/platforms")
async def get_platforms():
    try:
        platforms = helm_helper.get_platforms_list()
        return platforms

    except Exception as e:
        logger.error(f"/platforms FAILED {e}", exc_info=True)
        return Response(f"Failed to get platforms", 500)


@router.get("/available-platforms")
async def available_platforms(
    container_registry_url: str,
    encoded_auth: str = Query(...),
    platform_name: str = "kaapana-admin-chart",
    auth_url: str = "https://codebase.helmholtz.cloud/jwt/auth"
) -> List[str]:
    try:
        decoded = base64.b64decode(encoded_auth).decode()
        container_registry_username, container_registry_password = decoded.split(":", 1)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encoded_auth format")

    try:
        # Extract host and path
        registry_parts = container_registry_url.split('/')
        registry_host = registry_parts[0]
        registry_path = '/'.join(registry_parts[1:])

        scope = f"repository:{registry_path}/{platform_name}:pull"
        logger.info(f"Using scope: {scope}")

        # Get JWT token
        params = {
            "client_id": "docker",
            "offline_token": "true",
            "service": "container_registry",
            "scope": scope
        }
        logger.info(f"Fetching token from: {auth_url} with params: {params}")

        async with httpx.AsyncClient() as client:
            token_response = await client.get(
                auth_url,
                params=params,
                auth=(container_registry_username, container_registry_password),
                timeout=10.0,
            )
            token_response.raise_for_status()
            token_json = token_response.json()
            logger.info(f"Token response: {token_json}")
            token = token_json.get("token")

            if not token:
                raise HTTPException(status_code=401, detail="Authentication failed, token not received")

            # Get tags
            headers = {
                "Accept": "application/vnd.docker.distribution.manifest.v2+json",
                "Authorization": f"Bearer {token}"
            }
            tags_url = f"https://{registry_host}/v2/{registry_path}/{platform_name}/tags/list"
            logger.info(f"Fetching tags from: {tags_url}")

            tags_response = await client.get(tags_url, headers=headers)
            tags_response.raise_for_status()
            tags_json = tags_response.json()
            logger.info(f"Tags response: {tags_json}")
            tags = tags_json.get("tags", [])

        return sorted(tags, reverse=True)

    except httpx.TimeoutException:
        logger.error("Request timed out")
        raise HTTPException(status_code=504, detail="Gateway Timeout: The request to the container registry timed out.")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/view-chart-status")
async def view_chart_status(release_name: str):
    status = utils.helm_status(release_name)
    if status:
        return status
    else:
        return Response(f"Release not found", 404)
