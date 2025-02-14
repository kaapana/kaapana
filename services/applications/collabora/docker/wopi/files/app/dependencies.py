import functools
import requests
import xml.etree.ElementTree as ET
from app.model.websockets import ConnectionManager
from app.model.documents import DocumentStore
from app.model.wopi import WOPI
from app.config import get_settings
from fastapi import Request, Depends
from minio import Minio
import jwt
from kaapanapy.logger import get_logger

logger = get_logger(name=__name__)


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_access_token(request: Request):
    if "x-forwarded-access-token" in request.headers:
        return request.headers.get("x-forwarded-access-token")
    elif "authorization" in request.headers:
        bearer = request.headers.get("authorization")
        return bearer.split()[-1]


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

    access_key, secret_key, session_token = minio_credentials()

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


def get_username(request: Request):
    """
    Return the username as in the header x-forwarded-preferred-username.
    If this header does not exist, get the preferred_username from the access-token given in the authorization header.
    """
    if "x-forwarded-preferred-username" in request.headers:
        username = request.headers.get("x-forwarded-preferred-username")
    elif "authorization" in request.headers:
        bearer = request.headers.get("authorization")
        access_token = bearer.split()[-1]
        decoded_token = jwt.decode(
            access_token, algorithms=["RS256"], options={"verify_signature": False}
        )
        username = decoded_token.get("preferred_username")
    else:
        logger.warning("Username could not be determined")
        return None

    return username


@functools.lru_cache()
def get_document_store(username: str = Depends(get_username)) -> DocumentStore:
    # def get_document_store() -> DocumentStore:
    return DocumentStore()
