import requests
import os
import time

SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
SYSTEM_USER_PASSWORD = os.getenv("SYSTEM_USER_PASSWORD")


def get_system_user_token(
    ssl_check=False,
):
    payload = {
        "username": "system",
        "password": SYSTEM_USER_PASSWORD,
        "client_id": "kaapana",
        "client_secret": OIDC_CLIENT_SECRET,
        "grant_type": "password",
    }
    url = f"http://keycloak-external-service.admin.svc:80/auth/realms/kaapana/protocol/openid-connect/token"
    r = requests.post(url, verify=ssl_check, data=payload)
    access_token = r.json()["access_token"]
    return access_token


def check_file_on_platform(file, application_entity="KAAPANA", max_counter=100):
    access_token = get_system_user_token()
    counter = 0
    dcmweb_endpoint = (
        f"http://dcm4chee-service.{SERVICES_NAMESPACE}.svc:8080/dcm4chee-arc/aets"
    )
    while counter < max_counter:
        # quido file
        r = requests.get(
            f"{dcmweb_endpoint}/{application_entity}/rs/studies/{file['study_uid']}/series/{file['series_uid']}/instances",
            verify=False,
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-forwarded-access-token": access_token,
            },
        )

        if r.status_code != requests.codes.ok:
            counter += 1
            time.sleep(10)
        else:
            print("File successfully found in PACs")
            return True
    return False
