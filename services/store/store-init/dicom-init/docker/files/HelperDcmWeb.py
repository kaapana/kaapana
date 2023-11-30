import requests
import os
import time

SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")


class MyHelperDcmWeb:
    def __init__(self, username, application_entity, access_token=None):
        self.dcmweb_endpoint = (
            f"http://dcm4chee-service.{SERVICES_NAMESPACE}.svc:8080/dcm4chee-arc/aets"
        )
        self.application_entity = application_entity
        self.access_token = access_token
        self.system_user = "system"
        self.system_user_password = "admin"
        self.client_secret = OIDC_CLIENT_SECRET
        self.client_id = "kaapana"
        self.username = username
        if access_token:
            self.access_token = access_token
        elif self.username == self.system_user:
            self.access_token = self.get_system_user_token()
        else:
            self.access_token = self.impersonate_user()
        self.auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-forwarded-access-token": self.access_token,
        }

    def get_system_user_token(
        self,
        ssl_check=False,
    ):
        payload = {
            "username": self.system_user,
            "password": self.system_user_password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
        }
        url = f"http://keycloak-external-service.admin.svc:80/auth/realms/{self.client_id}/protocol/openid-connect/token"
        r = requests.post(url, verify=ssl_check, data=payload)
        access_token = r.json()["access_token"]
        return access_token

    def impersonate_user(self):
        admin_access_token = self.get_system_user_token()
        url = f"http://keycloak-external-service.admin.svc:80/auth/realms/{self.client_id}/protocol/openid-connect/token"
        data = {
            "client_id": self.client_id,
            "client_secret": OIDC_CLIENT_SECRET,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": admin_access_token,  # Replace with your actual subject_token
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "audience": "kaapana",
            "requested_subject": self.username,
        }

        r = requests.post(url, data=data, verify=False)
        impersonated_access_token = r.json()["access_token"]
        return impersonated_access_token

    def check_file_on_platform(self, file, max_counter=100):
        counter = 0
        while counter < max_counter:
            # quido file
            r = requests.get(
                f"{self.dcmweb_endpoint}/{self.application_entity}/rs/studies/{file['study_uid']}/series/{file['series_uid']}/instances",
                verify=False,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "x-forwarded-access-token": self.access_token,
                },
            )

            if r.status_code != requests.codes.ok:
                counter += 1
                time.sleep(10)
            else:
                print("File successfully found in PACs")
                return True
        return False
