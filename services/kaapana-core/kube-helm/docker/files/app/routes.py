import os
import secrets
import subprocess
import json
import yaml
import re

from flask import render_template, Response, request, jsonify
from app import app
from app import utils


@app.route("/")
@app.route("/index")
def index():

    return render_template(
        "index.html", title="Home",
    )


@app.route("/health-check")
def health_check():
    return Response(f"Kube-Helm api is up and running!", 200)


@app.route("/update-extensions")
def update_extensions():
    try:
        utils.helm_repo_index(app.config['HELM_COLLECTIONS_CACHE'])
    except subprocess.CalledProcessError as e:
        return Response(f"Could not create index.yaml!", 500)
        
    with open(os.path.join(app.config['HELM_COLLECTIONS_CACHE'], 'index.yaml'), 'r') as stream:
        try:
            extension_packages = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    install_error = False
    for chart_name, chart_versions  in extension_packages['entries'].items():
        for chart in chart_versions:
            print(chart['name'], chart['version'])
            release_name = f"{chart['name']}-{chart['version']}"

            payload = {k: chart[k] for k in ('name', 'version')}
            payload.update({'release_name': release_name})

            if not utils.helm_status(release_name, app.config['NAMESPACE']):
                try:
                    print(f'Installing {release_name}')
                    utils.helm_install(payload, app.config["NAMESPACE"], helm_cache_path=app.config['HELM_COLLECTIONS_CACHE'], in_background=False)
                except subprocess.CalledProcessError as e:
                    install_error = True
                    utils.helm_delete(release_name, app.config['NAMESPACE'])
                    print(e)
            else:
                try:
                    print('helm deleting and reinstalling')
                    helm_delete_prefix = f'{os.environ["HELM_PATH"]} uninstall -n {app.config["NAMESPACE"]} {release_name} --timeout 5m;'
                    utils.helm_install(payload, app.config["NAMESPACE"], helm_delete_prefix=helm_delete_prefix, helm_cache_path=app.config['HELM_COLLECTIONS_CACHE'], in_background=False)
                except subprocess.CalledProcessError as e:
                    install_error = True
                    utils.helm_delete(release_name, app.config['NAMESPACE'])
                    print(e)

    if install_error is False:
        return Response(f"Successfully updated the extensions", 202)
    else:
        return Response(f"We had troubles updating the extensions", 500)

@app.route("/helm-delete-chart")
def helm_delete_chart():
    release_name = request.args.get("release_name")
    release_version = request.args.get("release_version")
    try:
        utils.helm_delete(release_name=release_name, namespace=app.config['NAMESPACE'], release_version=release_version, )
        return jsonify({"message": "Successfully uninstalled", "status": "200"})
    except subprocess.CalledProcessError as e:
        return Response(f"We could not find the release you are trying to delete!", 500)


@app.route("/helm-install-chart", methods=["POST"])
def helm_add_custom_chart():
    print(request.json)
    try:
        resp, helm_command = utils.helm_install(request.json, app.config['NAMESPACE'])
        return Response(f"Trying to install chart with {helm_command}", 200)
    except:
        return Response(f"A helm command error occured while executing {helm_command}!", 500)


@app.route("/pull-docker-image", methods=["POST"])
def pull_docker_image():
    payload = request.json
    print(payload)
    release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
    try:
        utils.pull_docker_image(release_name, **payload)
        return Response(f"We are trying to download the docker container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 202)
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name, app.config['NAMESPACE'])
        print(e)
        return Response(f"We could not download your container {payload['docker_registry_url']}/{payload['docker_image']}:{payload['docker_version']}", 500)


@app.route("/prefetch-extension-docker")
def prefetch_extension_docker():
    print('prefechting')
    if app.config['OFFLINE_MODE'] is False:
        try:
            utils.helm_prefetch_extension_docker()
            return Response(f"Trying to prefetch all docker container of extensions", 200)
        except:
            return Response(f"An error occured!", 500)
    else:
        print('Offline mode is set to False!')
        return Response(f"We will not prefetch the extensions since the platform was installed with OFFLINE_MODE set to true!", 200)


@app.route("/pending-applications")
def pending_applications():
    try:
        extensions_list = []
        for chart in utils.helm_ls(app.config['NAMESPACE'], 'kaapanaint'):
            manifest = utils.helm_get_manifest(chart['name'], app.config['NAMESPACE'])
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


@app.route("/extensions")
def extensions():
    return json.dumps(utils.extensions_list_cached)


@app.route("/list-helm-charts")
def add_repo():
    try:
        resp = subprocess.check_output(f'{os.environ["HELM_PATH"]} ls -n {app.config["NAMESPACE"]} -o json', stderr=subprocess.STDOUT, shell=True)
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(f"{e.output}", 500)
    return resp


@app.route("/view-helm-env")
def view_helm_env():
    try:
        resp = subprocess.check_output(f'{os.environ["HELM_PATH"]} env', stderr=subprocess.STDOUT, shell=True)
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}", 500)
    return jsonify({"message": str(resp), "status": "200"})

@app.route("/view-chart-status")
def view_chart_status():
    release_name = request.args.get("release_name")
    status = utils.helm_status(release_name, app.config['NAMESPACE'])
    if status:
        return json.dumps(status)
    else:
        return Response(f"Release not found", 500)
