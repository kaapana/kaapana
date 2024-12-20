import functools
import requests
import xml.etree.ElementTree as ET
from app.model.websockets import ConnectionManager
from app.model.documents import DocumentStore
from app.model.wopi import WOPI
from app.config import get_settings
from fastapi import Request, Depends
from minio import Minio


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_access_token(request: Request):
    return request.headers.get("x-forwarded-access-token")


def get_minio_client(x_auth_token: str = Depends(get_access_token)) -> Minio:
    """
    :x_auth_token: Access token that should be used for communication with minio.
    """

    def minio_credentials():
        url = f"http://minio-service.services.svc:9000?Action=AssumeRoleWithWebIdentity&WebIdentityToken={x_auth_token}&Version=2011-06-15"
        r = requests.post(url)
        r.raise_for_status()
        xml_response = r.text
        root = ET.fromstring(xml_response)
        credentials = root.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}Credentials"
        )
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

    if x_auth_token:
        access_key, secret_key, session_token = minio_credentials()
    else:
        access_key, secret_key, session_token = "kaapanaminio", "Kaapana2020", None

    minio_url = f"minio-service.services.svc:9000"
    return Minio(
        minio_url,
        access_key=access_key,
        session_token=session_token,
        secret_key=secret_key,
        secure=False,
    )


@functools.lru_cache()
def get_wopi() -> WOPI:
    return WOPI(get_settings().collabora_url + "/hosting/discovery")


@functools.lru_cache()
def get_document_store() -> DocumentStore:
    return DocumentStore()
