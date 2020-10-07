import os
import copy
import secrets
import subprocess
import json
import yaml
import re
from flask import render_template, Response, request, jsonify
from app import app
from app import utils

repoName = 'kaapana'

available_charts = utils.helm_search_repo("(kaapanaextension|kaapanadag)")
# print(available_charts)
extensions_list = []
for extension in available_charts:
    repoName, chartName = extension["name"].split('/')
    chart = utils.helm_show_chart(repoName, chartName, extension['version'])
    status = utils.helm_status(chartName, app.config['NAMESPACE'])
    # print('chartName', chartName)
    # print('chart', chart)
    # print('status', status)
    # print('keywords', chart['keywords'])
    extension['keywords'] = chart['keywords']
    extension['releaseMame'] = extension["name"]
    extension['helm_status'] = 'uninstalled' 
    extension['kube_status'] = 'uninstalled' 
    if 'kaapanamultiinstallable' in chart['keywords'] or not status:
        extension['installed'] = 'no'
        extensions_list.append(extension)
    for chart in utils.helm_ls(app.config['NAMESPACE'], chartName):
        manifest = utils.helm_get_manifest(chart['name'], app.config['NAMESPACE'])
        ingress_path = ''
        for config in manifest:
            if config['kind'] == 'Ingress':
                ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
            if config['kind'] == 'Deployment':
                kube_status = get_kube_status('app',config['metadata']['name'], config['metadata']['namespace'])
            if config['kind'] == 'Job':
                kube_status = get_kube_status('job',config['metadata']['name'], config['metadata']['namespace'])
        running_extensions = copy.deepcopy(extension)
        running_extensions['releaseMame'] =  chart['name']
        running_extensions['link'] = ingress_path
        running_extensions['installed'] = 'yes'
        running_extensions['helm_status'] = chart['status']
        running_extensions['kube_status'] = kube_status['status']
        extensions_list.append(running_extensions)

print(extensions_list)


