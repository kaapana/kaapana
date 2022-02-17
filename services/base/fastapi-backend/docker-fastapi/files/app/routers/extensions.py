import os
import requests
import json

from fastapi import APIRouter, Response, HTTPException

_helm_host = os.getenv("KUBE_HELM_URL")
if not _helm_host:
  print("KUBE_HELM_URL not set")

router = APIRouter()

@router.get('/environment')
async def get_helm_environment():
    """ Return extension environment
    """
    url = _helm_host + '/view-helm-env'
    r = requests.get(url)
    return r.json()


@router.get('/installed')
def get_installed_extensions():
  """Return List of Installed Helm Charts
  To List Installed Helm Charts
  """
  url = _helm_host + '/extensions'
  r = requests.get(url)
  filteredList = [d for d in r.json() if d['installed'] =='yes']
  return filteredList


@router.get('/{name}/status')
def get_extension_status(name: str):
  """ To List  Chart Status
  """ 
  url = _helm_host + '/view-chart-status'
  r = requests.get(url, params={'release_name': name})
  
  return r.json()


@router.get('/')
def list_extensions():
    """Return List of Available Charts
    """
    url = _helm_host + '/extensions'
    r = requests.get(url)
    
    #TODO: return proper object
    return str(r.text)

@router.delete('/installed/{name}/{version}')
def delete_extension(name: str, version: str):
  """ Deletes an installed extensions
  """ 
  url = _helm_host + '/helm-delete-chart'
  r = requests.get(url, params={'release_name': name,'release_version': version})
  
  # TODO: retrun proper object
  return str(r.text)

@router.put('/installed/{name}')
def install_extension():
  """ To Install a  Chart (Recommended to call /list-available-charts/ first, to get the available charts to Install. The release_name parameter is only for multi-installer charts.  The release_name must follow this format. Chartname-<ustomname>. For example if chart name is mitk-workbench-chart, then the release_name  could be mitk-workbench-chart-customname)
  """ 

  # TODO what parameters are required for this?
  dicts = {}
  for value in request.json:
      dicts[value] = request.json[value]   
  print(dicts)
  url = _helm_host + '/helm-install-chart'
  r = requests.post(url,json=dicts)

  return str(r)
