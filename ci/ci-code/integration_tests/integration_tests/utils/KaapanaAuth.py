import json
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)


class KaapanaAuth:
    def __init__(
        self,
        host,
        client_secret=None,
        verify: bool = False,
        wait_for_platform: bool = True,
    ):
        """Initialize KaapanaAuth."""
        self.host = host
        self.client_secret = client_secret or os.environ.get("CLIENT_SECRET")
        if not self.client_secret:
            raise RuntimeError(
                "CLIENT_SECRET not provided to KaapanaAuth (argument or CLIENT_SECRET env)"
            )

        # create a session and configure TLS verification
        self.session = requests.Session()
        self.session.verify = verify
        if not verify:
            from requests.packages.urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        # --- NEW: WARM-UP PHASE ---
        if wait_for_platform:
            self.wait_for_ready()
        
        # obtain tokens and project info
        self.access_token = self.get_access_token()
        self.admin_project = self.get_admin_project()


    def get_admin_project(self):
        url = f"https://{self.host}/aii/projects/admin"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        r = self.session.get(url, headers=headers)
        r.raise_for_status()
        admin_project = r.json()
        return admin_project

    def wait_for_ready(self, timeout=120, interval=10):
        """
        Polls the Keycloak configuration endpoint to ensure the Ingress/Proxy
        is routing traffic correctly before we attempt a POST request.
        """
        # Using the well-known OIDC config endpoint as a health check
        url = (
            f"https://{self.host}/auth/realms/kaapana/.well-known/openid-configuration"
        )
        start_time = time.time()

        logger.info(
            f"Warming up: Checking if Kaapana platform at {self.host} is ready..."
        )

        while time.time() - start_time < timeout:
            try:
                # We use a simple GET here. If the proxy is still 'cold',
                # it might return 404/503/405, which we catch.
                r = self.session.get(url, timeout=5)
                if r.status_code == 200:
                    logger.info("Platform is ready. Proceeding to authentication.")
                    return True
                else:
                    logger.warning(
                        f"Platform returned {r.status_code}. Still waiting..."
                    )
            except requests.exceptions.RequestException as e:
                logger.debug(f"Connection attempt failed: {e}")

            time.sleep(interval)

        raise TimeoutError(
            f"Kaapana platform at {self.host} did not become ready within {timeout}s"
        )

    def get_access_token(
        self,
        username="kaapana",
        password="admin",
        protocol="https",
        port=443,
        ssl_check=False,
        client_id="kaapana",
        retries=5,  # number of attempts
        delay=3,  # seconds between attempts
    ):
        payload = {
            "username": username,
            "password": password,
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
                    logger.error(
                        f"Failed to get access token after {retries} attempts."
                    )
                    raise
                logger.warning(
                    f"Attempt {attempt} failed: {e}. Retrying in {delay}s..."
                )
                time.sleep(delay)

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

        method_name = getattr(request_type, "__name__", "get").lower()
        func = getattr(self.session, method_name, None)
        if func is None:
            func = request_type
        for attempt in range(retries):
            r = func(
                url=f"https://{self.host}/{endpoint}",
                json=_json,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                cookies={"Project": project_cookie},
            )
            if r.status_code < 400:
                break
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # exponential back-off: 1s, 2s, 4s, 8s
        if raise_for_status:
            r.raise_for_status()
        return r
