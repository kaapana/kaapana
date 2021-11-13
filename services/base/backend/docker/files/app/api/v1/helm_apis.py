
from flask import jsonify
from . import api_v1

from minio import Minio
import os
import requests
import json
from datetime import datetime
import socket
import subprocess
from flask import request


#Local Testing
#_helm_host='http://127.0.0.1:5001/kube-helm-api'

#Production URL 
_helm_host='http://kube-helm-service.kube-system.svc:5000/kube-helm-api'





@api_v1.route('/helm/helm-environment/')
def viewHelmEnv():
    """Return Helm Environment
    To List Buckets
    ---
    tags:
      - Helm APIs
   
    responses:
      200:
        description: Return Helm Environments
    """
    url = _helm_host + '/view-helm-env'
    r = requests.get(url)
   
    return r.json()


@api_v1.route('/helm/all-installed-charts/')
def listHelmCharts():
  """Return List of Installed Helm Charts
    To List Installed Helm Charts
    ---
    tags:
      - Helm APIs
   
    responses:
      200:
        description: Return List of Installed Helm Charts
    """
  url = _helm_host + '/extensions'
  r = requests.get(url)
  filteredList = [d for d in r.json() if d['installed'] =='yes']
  
  
  return str(filteredList)


@api_v1.route('/helm/chart-status/', methods=['GET'])
def view_chart_status():
    
  """
    To List  Chart Status
    ---
    tags:
      - Helm APIs
    parameters:
      - name: release_name
        in: query
        type: string
        required: true
        description: Enter chart release_name 
    responses:
      200:
        description: Success
    
  """ 
  release_name = request.args.get("release_name")
 
  url = _helm_host + '/view-chart-status'
  r = requests.get(url, params={'release_name': release_name})
  
  return str(r.text)
    
@api_v1.route('/helm/all-available-charts/')
def listExtensions():
    """Return List of Available Charts
    To List   Available Charts
    ---
    tags:
      - Helm APIs
   
    responses:
      200:
        description: Return List of List of Available Charts 
    """
    url = _helm_host + '/extensions'
    r = requests.get(url)
   
    return str(r.text)

@api_v1.route('/helm/chart-delete/', methods=['POST'])
def deleteChart():
    
  """
    To Delete a  Chart 
    ---
    tags:
      - Helm APIs
    parameters:
      - name: release_name
        in: query
        type: string
        required: true
        description: Enter chart release_name 
      - name: release_version
        in: query
        type: string
        required: false
        description: Enter chart release_version 
    responses:
      200:
        description: Success
    
  """ 
  release_name = request.args.get("release_name")
  release_version = request.args.get("release_version")
 
  url = _helm_host + '/helm-delete-chart'
  r = requests.get(url, params={'release_name': release_name,'release_version':release_version})
  
  return str(r.text)

@api_v1.route('/helm/install-chart/', methods=['POST'])
def installChart():
    
  """
    To Install a  Chart (Recommended to call /list-available-charts/ first, to get the available charts to Install. The release_name parameter is only for multi-installer charts.  The release_name must follow this format. Chartname-<ustomname>. For example if chart name is mitk-workbench-chart, then the release_name  could be mitk-workbench-chart-customname)
    ---
    tags:
      - Helm APIs
    parameters:
      - in: body
        name: chartsvalue
        description: The user to create.
        schema:
          type: object
          required:
            - name
            - version
          properties:
            name:
              type: string
            
            version:
              type: string
            release_name:
              type: string
    responses:
      200:
        description: Success
      500:
        description: Internal Error
    
  """ 

  
  dicts = {}
  for value in request.json:
      
      dicts[value] = request.json[value]   
  print(dicts)
  url = _helm_host + '/helm-install-chart'
  r = requests.post(url,json=dicts)

  return str(r)
