import requests
import os
import json as js
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class KaapanaAuth:
    def __init__(self, host, client_secret=None):
        self.host = host
        if client_secret:
            self.client_secret = client_secret
        else:
            self.client_secret = os.environ.get("CLIENT_SECRET")
        self.access_token = self.get_access_token(self.host, self.client_secret)

    def get_access_token(
        self,
        host,
        client_secret,
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
            "client_secret": client_secret,
            "grant_type": "password",
        }
        url = f"{protocol}://{host}:{port}/auth/realms/kaapana/protocol/openid-connect/token"
        r = requests.post(url, verify=ssl_check, data=payload)
        access_token = r.json()["access_token"]
        return access_token

    def request(
        self,
        endpoint,
        request_type=requests.get,
        json={},
        data={},
        params={},
        raise_for_status=True,
        timeout=10,
        retries=5,
        headers={},
    ):
        project_header = {
            "id": 1,
            "external_id": None,
            "name": "admin",
            "description": "Initial admin project",
        }
        headers.update({"Project": js.dumps(project_header)})
        headers.update({"Project-Name": "admin"})
        headers.update({"Authorization": f"Bearer {self.access_token}"})
        for _ in range(retries):
            r = request_type(
                url=f"https://{self.host}/{endpoint}",
                verify=False,
                json=json,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                cookies={"Project-Name": "admin"},
            )
            if r.status_code < 400:
                break
        if raise_for_status:
            r.raise_for_status()
        return r
