import json
import os
import xml.etree.ElementTree as ET

import requests
from kaapanapy.settings import KaapanaSettings, OpensearchSettings, OperatorSettings
from minio import Minio
from opensearchpy import OpenSearch


def get_opensearch_client(access_token=None):
    settings = OpensearchSettings()
    access_token = access_token or get_project_user_access_token()
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    return OpenSearch(
        hosts=[
            {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
            }
        ],
        http_compress=True,  # enables gzip compression for request bodies
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=10,
        headers=auth_headers,
    )


def get_minio_client(access_token=None):
    """
    :access_token: Access token that should be used for communication with minio.
    """
    access_token = access_token or get_project_user_access_token()
    access_key, secret_key, session_token = minio_credentials(access_token)

    return Minio(
        f"minio-service.{KaapanaSettings().services_namespace}.svc:9000",
        access_key=access_key,
        secret_key=secret_key,
        session_token=session_token,
        secure=False,
    )


def minio_credentials(access_token):
    r = requests.post(
        f"http://minio-service.{KaapanaSettings().services_namespace}.svc:9000?Action=AssumeRoleWithWebIdentity&WebIdentityToken={access_token}&Version=2011-06-15"
    )
    xml_response = r.text
    root = ET.fromstring(xml_response)
    credentials = root.find(".//{https://sts.amazonaws.com/doc/2011-06-15/}Credentials")
    access_key_id = credentials.find(
        ".//{https://sts.amazonaws.com/doc/2011-06-15/}AccessKeyId"
    ).text
    secret_access_key = credentials.find(
        ".//{https://sts.amazonaws.com/doc/2011-06-15/}SecretAccessKey"
    ).text
    session_token = credentials.find(
        ".//{https://sts.amazonaws.com/doc/2011-06-15/}SessionToken"
    ).text
    return access_key_id, secret_access_key, session_token


def get_project_user_access_token():
    """
    Return an access token of the project user.
    """
    from kaapanapy.settings import KeycloakSettings, ProjectSettings

    project_settings = ProjectSettings()
    keycloak_settings = KeycloakSettings()
    payload = {
        "username": project_settings.project_user_name,
        "password": project_settings.project_user_password,
        "client_id": keycloak_settings.client_id,
        "client_secret": keycloak_settings.client_secret,
        "grant_type": "password",
    }
    url = f"{keycloak_settings.keycloak_url}/auth/realms/{keycloak_settings.client_id}/protocol/openid-connect/token"
    r = requests.post(url, verify=False, data=payload)
    access_token = r.json()["access_token"]
    return access_token


def load_workflow_config():
    """
    Load and return the workflow config.
    """
    settings = OperatorSettings()
    config_path = os.path.join(settings.workflow_dir, "conf", "conf.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config
