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


@app.route("/helm-repo-update")
def helm_repo_update():
    try:
        resp = subprocess.check_output('helm repo update', stderr=subprocess.STDOUT, shell=True)
        print(resp)
        if 'server misbehaving' in resp.decode("utf-8"):
            return Response(f"You seem to have no internet connection inside the pod, this might be due to missing proxy settings!", 500)
        helm_command = 'helm repo update; \
            mkdir -p /root/\.extensions; \
            find /root/\.extensions -type f -delete;' + \
            f'helm pull -d /root/.extensions/ --version={app.config["VERSION"]} {app.config["CHART_REGISTRY_PROJECT"]}/pull-docker-chart;' + \
            'helm search repo --devel -l -r \'(kaapanaworkflow|kaapanaapplication|kaapanaint)\' -o json | jq -r \'.[] | "\(.name) --version \(.version)"\' | xargs -L1 helm pull -d /root/\.extensions/'
        subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True)
        return Response(f"Successfully updated the extension list!", 200)
    except subprocess.CalledProcessError as e:
        return Response(f"A helm command error occured while executing {helm_command}! Error {e}", 500)


@app.route("/helm-delete-chart")
def helm_delete_chart():
    release_name = request.args.get("release_name")
    try:    
        utils.helm_delete(release_name, app.config['NAMESPACE'])
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
        return Response(f"We are trying to download the docker container {payload['docker_registry_url']}{payload['docker_registry_project']}/{payload['docker_image']}:{payload['docker_version']}", 202)
    except subprocess.CalledProcessError as e:
        utils.helm_delete(release_name, app.config['NAMESPACE'])
        print(e)
        return Response(f"We could not download your container {payload['docker_registry_url']}{payload['docker_registry_project']}/{payload['docker_image']}:{payload['docker_version']}", 500)


@app.route("/prefetch-extension-docker")
def prefetch_extension_docker():
    print('prefechting')
    utils.helm_prefetch_extension_docker()
    try:
        
        return Response(f"Trying to prefetch all docker container of extensions", 200)
    except:
        return Response(f"A error occured!", 500)


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
        return Response(f"{e.output}",500)
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
            f"{e.output}",500)
    return jsonify({"message": str(resp), "status": "200"})


@app.route("/helm-repo-list")
def helm_repo_list():
    try:
        resp = subprocess.check_output(f'{os.environ["HELM_PATH"]} repo list -o json', stderr=subprocess.STDOUT, shell=True) 
        return resp
    except subprocess.CalledProcessError as e:
        return Response(f"{e.output}", 500)
    return resp


@app.route("/view-chart-status")
def view_chart_status():
    release_name = request.args.get("release_name")
    status = utils.helm_status(release_name, app.config['NAMESPACE'])
    if status:
        return json.dumps(status)
    else:
        return Response(f"Release not found", 500)
