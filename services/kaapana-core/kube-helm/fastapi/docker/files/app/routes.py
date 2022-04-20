import os
import secrets
import subprocess
import json
import yaml

from fastapi import APIRouter,Response, Request
from fastapi.templating import Jinja2Templates
from app import utils
from .config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
@router.get("/index")
def index():
    return templates.TemplateResponse("index.html")


@router.get("/health-check")
def health_check():
    # TODO return JSON object
    return Response(f"Kube-Helm api is up and running!", 200)


@router.get("/update-extensions")
def update_extensions():
    if settings.offline_mode is True:
        return Response(f"We will not prefetch the extensions since the platform runs in offline mode!", 200)
    try:
        utils.helm_repo_index(settings.helm_collections_cache)
    except subprocess.CalledProcessError as e:
        return Response(f"Could not create index.yaml!", 500)
        
    with open(os.path.join(settings.helm_collections_cache, 'index.yaml'), 'r') as stream:
        try:
            extension_packages = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    install_error = False
    for _, chart_versions  in extension_packages['entries'].items():
        for chart in chart_versions:
            print(chart['name'], chart['version'])
            release_name = f"{chart['name']}-{chart['version']}"

            payload = {k: chart[k] for k in ('name', 'version')}
            payload.update({'release_name': release_name})

            if not utils.helm_status(release_name, settings.namespace):
                try:
                    print(f'Installing {release_name}')
                    utils.helm_install(payload, settings.namespace, helm_cache_path=settings.helm_collections_cache, in_background=False)
                except subprocess.CalledProcessError as e:
                    install_error = True
                    utils.helm_delete(release_name, settings.namespace)
                    print(e)
            else:
                try:
                    print('helm deleting and reinstalling')
                    helm_delete_prefix = f'{os.environ["HELM_PATH"]} uninstall -n {settings.namespace} {release_name} --timeout 5m;'
                    utils.helm_install(payload, settings.namespace, helm_delete_prefix=helm_delete_prefix, helm_cache_path=settings.helm_collections_cache, in_background=False)
                except subprocess.CalledProcessError as e:
                    install_error = True
                    utils.helm_delete(release_name, settings.namespace)
                    print(e)

    if install_error is False:
        return Response(f"Successfully updated the extensions", 202)
    else:
        return Response(f"We had troubles updating the extensions", 500)

@router.get("/helm-delete-chart")
def helm_delete_chart(release_name: str, release_version: str):
    try:
        utils.helm_delete(release_name=release_name, namespace=settings.namespace, release_version=release_version, )
        return {"message": "Successfully uninstalled", "status": "200"}
    except subprocess.CalledProcessError as e:
        return Response(f"We could not find the release you are trying to delete!", 500)


@router.post("/helm-install-chart")
def helm_add_custom_chart(request: Request):
    # TODO check if chart already exists and return https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/409
    print(request.json)
    try:
        resp, helm_command = utils.helm_install(request.json, settings.namespace)
        return Response(f"Trying to install chart with {helm_command}", 200)
    except:
        return Response(f"A helm command error occured while executing {helm_command}!", 500)


@router.post("/pull-docker-image")
def pull_docker_image(request: Request):
    payload = request.json
    print(payload)
    release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
    try:
        utils.pull_docker_image(release_name, **payload)
        return Response(f"We are trying to download the docker container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 202)
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name, settings.namespace)
        print(e)
        return Response(f"We could not download your container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 500)


@router.get("/prefetch-extension-docker")
def prefetch_extension_docker():
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
def pending_applications():
    try:
        extensions_list = []
        for chart in utils.helm_ls(settings.namespace, 'kaapanaint'):
            manifest = utils.helm_get_manifest(chart['name'],settings.namespace)
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
    return json.dumps(extensions_list)


@router.get("/extensions")
def extensions():
    return json.dumps(utils.extensions_list_cached)


@router.get("/list-helm-charts")
def add_repo():
    try:
        resp = subprocess.check_output(f'{os.environ["HELM_PATH"]} ls -n {settings.namespace} -o json', stderr=subprocess.STDOUT, shell=True)
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(f"{e.output}", 500)
    return resp


@router.get("/view-helm-env")
def view_helm_env():
    try:
        resp = subprocess.check_output(f'{os.environ["HELM_PATH"]} env', stderr=subprocess.STDOUT, shell=True)
        # TODO parse response to json object
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}", 500)
    return {"message": str(resp), "status": "200"}

@router.get("/view-chart-status")
def view_chart_status(release_name: str):
    status = utils.helm_status(release_name, settings.namespace)
    if status:
        return json.dumps(status)
    else:
        return Response(f"Release not found", 404)
