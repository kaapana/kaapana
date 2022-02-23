import os
import requests
import json
from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import JSONResponse

_helm_host = os.getenv("KUBE_HELM_URL")
if not _helm_host:
  print("KUBE_HELM_URL not set")

router = APIRouter()

def get_helm_api_json(url, params=None, text_response=False):
  url = _helm_host + url
  r = requests.get(url, params=params)
  if text_response:
    return { "message": r.text, "status_code": r.status_code }
  else:
    return r.json()

@router.get('/environment')
async def get_helm_environment():
  """ Return extension environment
  """
  return get_helm_api_json('/view-helm-env')


@router.get('/installed')
async def get_installed_extensions():
  """Return List of Installed Helm Charts
  To List Installed Helm Charts
  """
  obj = get_helm_api_json('/extensions')
  filteredList = [d for d in obj if d['installed'] =='yes']
  return filteredList


@router.get('/{name}/status')
async def get_extension_status(name: str):
  """ To List  Chart Status
  """
  return get_helm_api_json('/view-chart-status', params={'release_name': name})


@router.get('/')
async def list_extensions():
  """Return list of available Charts
  """
  return get_helm_api_json('/extensions')

@router.delete('/installed/{name}/{version}')
async def delete_extension(name: str, version: str):
  """ Deletes an installed extensions
  """ 
  return get_helm_api_json('/helm-delete-chart', params={'release_name': name,'release_version': version})



class ChartInstallation(BaseModel):
  """
  payload = {
              'name': f'{self.chart_name}',
              'version': self.version,
              'release_name': release_name,
              'sets': {
                  'mount_path': f'{self.data_dir}/{kwargs["run_id"]}',
                  "workflow_dir": str(WORKFLOW_DIR),
                  "batch_name": str(BATCH_NAME),
                  "operator_out_dir": str(self.operator_out_dir),
                  "operator_in_dir": str(self.operator_in_dir),
                  "batches_input_dir": "/{}/{}".format(WORKFLOW_DIR, BATCH_NAME)
              }
          }
  """
  name: str
  version: str
  keywords: Optional[List[str]]
  sets: Optional[Dict]
  release_name: Optional[str]

@router.put('/installed/')
async def install_extension(installation: ChartInstallation):
  """ To Install a  Chart (Recommended to call /list-available-charts/ first, to get the available charts to Install. The release_name parameter is only for multi-installer charts.  The release_name must follow this format. Chartname-<ustomname>. For example if chart name is mitk-workbench-chart, then the release_name  could be mitk-workbench-chart-customname)
  """ 
  url = _helm_host + '/helm-install-chart'
  r = requests.post(url,json=installation.dict(exclude_none=True))
  resp = {
    "message": r.text
  }
  return JSONResponse(status_code=r.status_code, content=resp)

@router.get('/health')
async def get_health():
  """ Status of the underlying api """
  return get_helm_api_json('/health-check', text_response=True)

@router.get('/reload')
async def reload_extesions_list():
  """ Reloads the local extensions """
  return get_helm_api_json('/update-extensions', text_response=True)

@router.get('/update')
async def update_extesions_list():
  """ Download new extensions from registry """
  return get_helm_api_json('/prefetch-extension-docker', text_response=True)

@router.get('/pending')
async def pending():
  return get_helm_api_json('/pending-applications')

# pull-docker-image
# TODO: Staring applications get @router.get('/running')
# list-helm-charts --> /extensions 