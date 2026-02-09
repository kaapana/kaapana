import json
import os

import requests


class KaapanaAuth:
    def __init__(self, host, client_secret=None):
        self.host = host
        self.client_secret = client_secret or os.environ.get("CLIENT_SECRET")
        if not self.client_secret:
            raise RuntimeError("CLIENT_SECRET not provided to KaapanaAuth (argument or CLIENT_SECRET env)")
        self.access_token = self.get_access_token()
        self.admin_project = self.get_admin_project()

    def get_admin_project(self):
        url = f"https://{self.host}/aii/projects/admin"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        r = requests.get(url, verify=False, headers=headers)
        r.raise_for_status()
        admin_project = r.json()
        return admin_project

    def get_access_token(
        self,
        username="kaapana",
        password="admin",
        protocol="https",
        port=443,
        ssl_check=False,
        client_id="kaapana",
    ):
        payload = {
            "username": username,
            "password": password,
            "client_id": client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
        }
        url = f"{protocol}://{self.host}:{port}/auth/realms/kaapana/protocol/openid-connect/token"
        r = requests.post(url, verify=ssl_check, data=payload)
        access_token = r.json()["access_token"]
        return access_token

    def request(
        self,
        endpoint,
        request_type=requests.get,
        _json={},
        data={},
        params={},
        raise_for_status=True,
        timeout=30,
        retries=5,
        headers={},
    ):
        project_header = {
            "id": self.admin_project["id"],
            "external_id": self.admin_project["external_id"],
            "name": self.admin_project["name"],
            "description": self.admin_project["description"],
        }
        headers.update({"Project": json.dumps(project_header)})
        headers.update({"Authorization": f"Bearer {self.access_token}"})
        project_cookie = json.dumps(
            {
                "name": self.admin_project["name"],
                "id": self.admin_project["id"],
            }
        )

        for _ in range(retries):
            r = request_type(
                url=f"https://{self.host}/{endpoint}",
                verify=False,
                json=_json,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                cookies={"Project": project_cookie},
            )
            if r.status_code < 400:
                break
        if raise_for_status:
            r.raise_for_status()
        return r
