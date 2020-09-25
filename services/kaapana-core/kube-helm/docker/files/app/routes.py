import os
from flask import render_template, Response, request, jsonify
from app import app
import subprocess, json

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
    chartname = request.args.get("chart")
    # print('chart name:', chartname)
    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "status", chartname, "-o", "json"],
            stderr=subprocess.STDOUT,
        )

    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return resp


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


@app.route("/helm-install-chart", methods=["POST"])
def helm_add_custom_chart():
    """A API response for adding helm charts from jip registry

    Arguments:
        config file {json} -- A json contains custom values for installing helm charts. It must contain meta tags repoName,
        chartName,version. The sets tag is not mandatory
    Returns:
        json: A json response about the installed chart
    """
    userConfig = ""
    content = request.json
    print(content)
    repoName = content["repoName"]
    chartName = content["chartName"]
    version = content["version"]

    if "customName" in content:
        custom_name = content["customName"]
    else:
        custom_name = content["chartName"]

    if "sets" in content:
        for i in content["sets"]:
            userConfig += " --set " + i + "=" + content["sets"][i]

    try:
        resp = subprocess.check_output(
            [
                os.environ["HELM_PATH"]
                + " install"
                + " "
                + userConfig
                + " "
                + "--version"
                + " "
                + version
                + " "
                + custom_name
                + " "
                + repoName
                + "/"
                + chartName
                + " -o"
                + " json"
            ],
            shell=True,
            stderr=subprocess.STDOUT,
        )

    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )

    return resp


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
    chartName = request.args.get("chart")

    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "uninstall", chartName], stderr=subprocess.STDOUT
        )

    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
        )
    return jsonify({"message": str(resp), "status": "200"})


# end of lines
