import requests
import json
import logging
from typing import Optional, List, Dict

class ExtensionService:
    def __init__(self, helm_api: str):
        self.helm_api = helm_api
        self.log = logging.getLogger(__name__)
        self.log.info("Initalized ExtensionService (using %s as endpoint", helm_api)

    def get_helm_api_json(self, url, params=None, text_response=False):
        url = self.helm_api + url
        r = requests.get(url, params=params)
        if text_response:
            return { "message": r.text, "status_code": r.status_code }
        else:
            return r.json()

    def get_environment(self):
        return self.get_helm_api_json('/view-helm-env')

    def installed(self):
        obj = self.get_helm_api_json('/extensions')
        filteredList = [d for d in obj if d['installed'] =='yes']
        return filteredList

    def status(self, name: str):
        return self.get_helm_api_json('/view-chart-status', params={'release_name': name})

    def all(self):
        return self.get_helm_api_json('/extensions')

    def delete(self, name: str, version: str):
        r = requests.post(self.helm_api + '/helm-delete-chart', params={'release_name': name,'release_version': version})
        if not r.ok:
            raise Exception(f"Return status: {r.status_code}: {r.text}")
        return { "message": r.text, "status_code": r.status_code }

    def health(self):
        return self.get_helm_api_json('/health-check', text_response=True)

    def reload(self):
        return self.get_helm_api_json('/update-extensions', text_response=True)

    def update(self):
        return self.get_helm_api_json('/prefetch-extension-docker', text_response=True)

    def pending(self):
        return self.get_helm_api_json('/pending-applications')

    def install(self,
                name: str,
                version: str,
                release_name: Optional[str],
                keywords: Optional[List[str]],
                parameters: Optional[Dict[str,str]]):
        url = self.helm_api + '/helm-install-chart'
        # payload = {
        #     'name': f'{self.chart_name}',
        #     'version': self.version,
        #     'release_name': release_name,
        #     'sets': {
        #         'mount_path': f'{self.data_dir}/{kwargs["run_id"]}',
        #         "workflow_dir": str(WORKFLOW_DIR),
        #         "batch_name": str(BATCH_NAME),
        #         "operator_out_dir": str(self.operator_out_dir),
        #         "operator_in_dir": str(self.operator_in_dir),
        #         "batches_input_dir": "/{}/{}".format(WORKFLOW_DIR, BATCH_NAME)
        #     }
        # }
        payload = {
            'name': name,
            'version': version,
        }
        if release_name:
            payload['release_name'] = release_name
        if keywords:
            payload['keywords'] = keywords
        if parameters:
            payload['sets'] = parameters

        r = requests.post(url, json=payload)
        if not r.ok:
            raise Exception(f"Return status: {r.status_code}: {r.text}")
        return { "message": r.text, "status_code": r.status_code }