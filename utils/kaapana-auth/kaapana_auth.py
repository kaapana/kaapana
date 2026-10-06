import logging
import os
import re
import time

import requests
import urllib3

logger = logging.getLogger(__name__)

PROJECT_SCOPED = re.compile(r"^/?(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)(/|$)")


class KaapanaAuth:
    def __init__(
        self,
        host,
        client_secret=None,
        verify: bool = False,
        wait_for_platform: bool = True,
        username: str = "kaapana",
        password: str = "admin",
    ):
        self.host = host.split("://")[-1].rstrip("/")
        self.username = username
        self.password = password
        self.client_secret = client_secret or os.environ.get("CLIENT_SECRET")
        if not self.client_secret:
            raise RuntimeError("CLIENT_SECRET not provided to KaapanaAuth (argument or CLIENT_SECRET env)")

        self.session = requests.Session()
        self.session.verify = verify
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if wait_for_platform:
            self.wait_for_ready()

        self._airflow_session = False
        self.access_token = self.get_access_token()
        self.admin_project = self.get_admin_project()

    def _scoped(self, endpoint):
        if PROJECT_SCOPED.match(endpoint):
            slug = self.admin_project["short_id"]
            return f"project/{slug}/{endpoint.lstrip('/')}"
        return endpoint

    def get_admin_project(self):
        url = f"https://{self.host}/aii/projects/admin"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        r = self.session.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

    def wait_for_ready(self, timeout=120, interval=10):
        url = f"https://{self.host}/auth/realms/kaapana/.well-known/openid-configuration"
        start_time = time.time()

        logger.info(f"Warming up: Checking if Kaapana platform at {self.host} is ready...")

        while time.time() - start_time < timeout:
            try:
                r = self.session.get(url, timeout=5)
                if r.status_code == 200:
                    logger.info("Platform is ready. Proceeding to authentication.")
                    return True
                logger.warning(f"Platform returned {r.status_code}. Still waiting...")
            except requests.exceptions.RequestException as e:
                logger.debug(f"Connection attempt failed: {e}")

            time.sleep(interval)

        raise TimeoutError(f"Kaapana platform at {self.host} did not become ready within {timeout}s")

    def get_access_token(
        self,
        username=None,
        password=None,
        protocol="https",
        port=443,
        ssl_check=False,
        client_id="kaapana",
        retries=5,
        delay=3,
    ):
        payload = {
            "username": username or self.username,
            "password": password or self.password,
            "client_id": client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
        }
        url = f"{protocol}://{self.host}:{port}/auth/realms/kaapana/protocol/openid-connect/token"

        for attempt in range(1, retries + 1):
            try:
                r = self.session.post(url, verify=ssl_check, data=payload)
                r.raise_for_status()
                access_token = r.json()["access_token"]
                logger.info(f"Access token acquired on attempt {attempt}")
                return access_token
            except requests.exceptions.RequestException as e:
                if attempt == retries:
                    logger.error(f"Failed to get access token after {retries} attempts.")
                    raise
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

    def airflow_login(self):
        r = self.session.get(
            f"https://{self.host}/flow/login/",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        r.raise_for_status()
        self._airflow_session = True

    def refresh(self):
        self.access_token = self.get_access_token()
        if self._airflow_session:
            self.airflow_login()

    def request(
        self,
        endpoint,
        request_type=requests.get,
        _json={},
        data={},
        params={},
        raise_for_status=True,
        timeout=120,
        retries=5,
        headers={},
    ):
        method_name = getattr(request_type, "__name__", "get").lower()
        func = getattr(self.session, method_name, None)
        if func is None:
            func = request_type
        refreshed = False
        attempt = 0
        while True:
            r = func(
                url=f"https://{self.host}/{self._scoped(endpoint)}",
                json=_json,
                data=data,
                params=params,
                headers={**headers, "Authorization": f"Bearer {self.access_token}"},
                timeout=timeout,
            )
            if r.status_code < 400:
                break
            if r.status_code == 401 and not refreshed:
                self.refresh()
                refreshed = True
                continue
            attempt += 1
            if attempt >= retries:
                break
            time.sleep(2 ** (attempt - 1))
        if raise_for_status:
            r.raise_for_status()
        return r
