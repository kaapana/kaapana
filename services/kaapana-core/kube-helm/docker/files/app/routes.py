import os
import copy
from flask import render_template, Response, request, jsonify
from app import app
from app import utils
import subprocess, json
import yaml
import secrets

"""
Welcome Page
"""


@app.route("/")
@app.route("/index")
def index():
    """Returns a welcome page

    Returns:
        html: a html welcome page
    """
    hello_world_user = os.environ["HELLO_WORLD_USER"]

    return render_template(
        "index.html", title="Home", hello_world_user=hello_world_user
    )


"""
The /list-helm-charts will list the currently installed helm charts in your environment
"""

@utils.helm_repo_update_decorator
@app.route("/list-helm-charts")
def add_repo():
    """Return a list of helm charts installed in the environment

    Returns:
        json: A json response with installed charts
    """
    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "ls", "-o", "json"], stderr=subprocess.STDOUT
        )
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return resp


"""
The /view-helm-env will list your helm installation and its environment values
"""


@app.route("/view-helm-env")
def view_helm_env():
    """A API response with  a list of helm environment variables from the system

    Returns:
        json: Return a json with helm env variables
    """

    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "env"], stderr=subprocess.STDOUT
        )
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return jsonify({"message": str(resp), "status": "200"})


"""
The /helm-repo-list will list your installed helm repositories
"""

@utils.helm_repo_update_decorator
@app.route("/helm-repo-list")
def helm_repo_list():
    """A API response with installed helm repositories

    Returns:
        json: A json with installed helm repositories
    """
    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "repo", "list", "-o", "json"],
            stderr=subprocess.STDOUT,
        )
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return resp


"""
The /view-chart-status will provide informations about your chart,last deployed, status, revision etc.
"""


@app.route("/view-chart-status")
def view_chart_status():
    """A API response with installed helm charts status

    Arguments:
        key : chart
        value: the chart name to be viewed

    Returns:
        json: returns installed charts and its property values
    """
    release_name = request.args.get("release_name")
    status = utils.helm_status(release_name, app.config['NAMESPACE'])
    if status:
        return json.dumps(status)
    else:
        return Response(
            f"Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )


"""
The /helm-add-repo to add new repositories
"""


@app.route("/helm-add-repo")
def helm_add_repo():
    """A API response for adding helm repositories from dktk jip registry

    Arguments:
        key : repo
        value: the repo name to be added

    Returns:
        json: A json response with added repo details from dktk jip registry
    """
    repoName = request.args.get("repo")

    try:
        resp = subprocess.check_output(
            [
                os.environ["HELM_PATH"],
                "repo",
                "add",
                repoName,
                "https://dktk-jip-registry.dkfz.de/chartrepo/" + repoName,
            ],
            stderr=subprocess.STDOUT,
        )
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return jsonify({"message": str(resp), "status": "200"})


"""
The /helm-remove-repo to add remove the existing repositories
"""


@app.route("/helm-remove-repo")
def helm_remove_repo():
    """A API response for removing repo from dktk jip registry

    Arguments:
        key : repo
        value: the repo name to be uninstalled

    Returns:
        json: A json response with removed repo
    """

    repoName = request.args.get("repo")

    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "repo", "remove", repoName],
            stderr=subprocess.STDOUT,
        )
        print(resp)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return jsonify({"message": str(resp), "status": "200"})


"""
custom parameters to install chart 
"""

@utils.helm_repo_update_decorator
@app.route("/helm-install-chart", methods=["POST"])
def helm_add_custom_chart():
    """A API response for adding helm charts from jip registry

    Arguments:
        config file {json} -- A json contains custom values for installing helm charts. It must contain meta tags repoName,
        chartName,version. The sets tag is not mandatory
    Returns:
        json: A json response about the installed chart
    """

    return utils.helm_install(request.json, app.config['NAMESPACE'])

"""
custom parameters to install chart 
"""


@app.route("/helm-install-extension", methods=["POST"])
def helm_install_extension():
    """A API response for adding helm charts from jip registry

    Arguments:
        config file {json} -- A json contains custom values for installing helm charts. It must contain meta tags repoName,
        chartName,version. The sets tag is not mandatory
    Returns:
        json: A json response about the installed chart
    """
    content = request.json

    content['sets'] = {
            'global.registry_url': 'dktk-jip-registry.dkfz.de',
            'global.registry_project':  '/kaapana',
            'global.base_namespace': 'flow-jobs',
            'global.fast_data_dir': '/home/kaapana/dicom/minio',
            'global.slow_data_dir': '/home/kaapana/dicom/minio',
        }
    repoName, chartName = content["name"].split('/')
    version = content["version"]
    multi_installable = content["multi_installable"]
    if multi_installable == 'yes':
        suffix = secrets.token_hex(5)
        content['customName'] = f'{chartName}-{suffix}'
        content['sets']['ingress_path'] = f'/{content["customName"]}'
        content['sets']['multi_instance_suffix'] = suffix

    print('content', content)
    return utils.helm_install(content, app.config['NAMESPACE'])


"""
The /helm-uninstall-chart to uninstall the existing helm charts
"""


@app.route("/helm-uninstall-chart")
def helm_uninstall_chart():
    """Return a API response for uninstalling a helm chart

    Arguments:
        key : chart
        value: the chart name to be uninstalled

    Returns:
        json: A json response with status code and message from helm
    """
    release_name = request.args.get("release_name")

    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", app.config['NAMESPACE'], "uninstall", release_name], stderr=subprocess.STDOUT
        )

    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return jsonify({"message": str(resp), "status": "200"})


@utils.helm_repo_update_decorator
@app.route("/pending-applications")
def pending_applications():
    try:
        extensions_list = []
        for chart in utils.helm_ls(app.config['NAMESPACE'], 'kaapanaint'):
            manifest = utils.helm_get_manifest(chart['name'], app.config['NAMESPACE'])
            ingress_path = ''
            for config in manifest:
                if config['kind'] == 'Ingress':
                    ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
            extension = {
                'name': chart['name'],
                'link': ingress_path
            }            
            extensions_list.append(extension)

    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return json.dumps(extensions_list)


@utils.helm_repo_update_decorator
@app.route("/extensions")
def extensions():
    """A API response to get all installable charts from repo

    Arguments:
        key : repo
        value: repo name

    Returns:
        json: returns the json response with all installable charts
    """
    repoName = request.args.get("repo")

    # TODO: add repoName to regex
    try:
        available_charts = utils.helm_search_repo("kaapanaextension")
        extensions_list = []
        for extension in available_charts:
            repoName, chartName = extension["name"].split('/')
            chart_values = utils.helm_show_values(repoName, chartName, extension['version'])
            if 'multi_installable' in chart_values:
                extension['multi_installable'] = 'yes'
            else:
                extension['multi_installable'] = 'no'

            installed_values = utils.helm_get_values(chartName, app.config['NAMESPACE'])
            if 'multi_instance_suffix' in installed_values or not installed_values:
                extension['installed'] = 'no'
                extensions_list.append(extension)
            for chart in utils.helm_ls(app.config['NAMESPACE'], chartName):
                manifest = utils.helm_get_manifest(chart['name'], app.config['NAMESPACE'])
                ingress_path = ''
                for config in manifest:
                    if config['kind'] == 'Ingress':
                        ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
                running_extensions = copy.deepcopy(extension)
                running_extensions['name'] =  chart['name']
                running_extensions['link'] = ingress_path
                running_extensions['installed'] = 'yes'
                extensions_list.append(running_extensions)

    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return json.dumps(extensions_list)

    # End of Lines
