import os
import yaml
import functools
import subprocess, json
from flask import render_template, Response, request, jsonify


def helm_repo_update_decorator(func):
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        # Do something before
        repoUpdated = subprocess.check_output(
            [os.environ["HELM_PATH"], "repo", "update"], stderr=subprocess.STDOUT
        )
        print(repoUpdated)
        value = func(*args, **kwargs)
        return value
    return wrapper_decorator

def helm_show_values(repo, name, version):
    try:
        chart = subprocess.check_output(
            [os.environ["HELM_PATH"], "show", "values", f"--version={version}", f"{repo}/{name}"], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return []
    return yaml.load(chart)

def helm_get_manifest(release_name, namespace):
    try:
        manifest = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "get", "manifest", release_name], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return []
    return list(yaml.load_all(manifest))    

def helm_get_values(release_name, namespace):
    try:
        values = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "get", "values", "-o", "json", release_name], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return dict()
    if values==b'null\n':
        return dict()
    return json.loads(values)


def helm_status(release_name, namespace):
    try:
        status = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "status", release_name], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return dict()
    return yaml.load(status)

def helm_install(content, namespace):
    repoName, chartName = content["name"].split('/')
    version = content["version"]

    if "customName" in content:
        custom_name = content["customName"]
    else:
        custom_name = chartName

    status = helm_status(custom_name, namespace)
    if status:
        chart = helm_show_values(repoName, chartName, version)
        if 'multi_instance_suffix' in chart:
            print('Installing again with multi_instance_suffix')
        else:
            return Response(
                "installed",
                200,
            )
    userConfig = []
    if "sets" in content:
        for key, value in content["sets"].items():
            userConfig = userConfig + ["--set", f"{key}={value}"]
            
    try:
        print(userConfig)
        resp = subprocess.check_output(
            [
                os.environ["HELM_PATH"],
                "install",
                "-n",
                "default",
                "--version",
                version,
                custom_name
            ] + 
                userConfig + [
                f"{repoName}/{chartName}",
                "-o",
                "json",
                "--wait",
                "--atomic",
                "--timeout",
                "10m0s"
            ],
            stderr=subprocess.STDOUT
        )
        return Response(resp, 200)
    except subprocess.CalledProcessError as e:
        return Response(
            f"{e.output}Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401
        )

def helm_ls(namespace, release_filter=''):
    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "--filter", release_filter, "ls", "-o", "json"], stderr=subprocess.STDOUT
        )
        return  json.loads(resp)
    except subprocess.CalledProcessError as e:
        return []
        
def helm_search_repo(filter_regex):   
    resp = subprocess.check_output(
        [
            os.environ["HELM_PATH"],
            "search",
            "repo",
            "--devel",
            "-r",
            filter_regex,
            "-o",
            "json",
        ],
        stderr=subprocess.STDOUT,
    )
    print(resp)
    try:
        data = json.loads(resp)
    except json.decoder.JSONDecodeError as e:
        print('No results found', e)
        data = []
    return data