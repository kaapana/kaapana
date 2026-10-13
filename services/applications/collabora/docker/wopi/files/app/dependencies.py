import functools
import json
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import jwt
import requests
from app.config import get_settings
from app.model.websockets import ConnectionManager
from app.model.wopi import WOPI
from fastapi import Depends, HTTPException, Request
from minio import Minio

log = logging.getLogger("uvicorn.error")

STS_NAMESPACE = "{https://sts.amazonaws.com/doc/2011-06-15/}"
BUCKET_PREFIX = "project-"
WRITE_POLICY = "admin_project"
ADMIN_POLICY = "consoleAdmin"


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_access_token(request: Request) -> Optional[str]:
    if "x-forwarded-access-token" in request.headers:
        return request.headers.get("x-forwarded-access-token")
    elif "authorization" in request.headers:
        bearer = request.headers.get("authorization")
        return bearer.split()[-1]
    return request.query_params.get("access_token")


def minio_credentials(access_token: str) -> tuple[str, str, str]:
    try:
        response = requests.post(
            f"http://{get_settings().minio_url}",
            params={
                "Action": "AssumeRoleWithWebIdentity",
                "WebIdentityToken": access_token,
                "Version": "2011-06-15",
            },
            timeout=10,
        )
    except requests.RequestException as error:
        log.error("MinIO STS request failed: %s", error)
        raise HTTPException(502, "Object storage is not reachable")
    if 400 <= response.status_code < 500:
        raise HTTPException(401, "Access token was rejected by the object storage")
    if not response.ok:
        log.error("MinIO STS answered %i: %s", response.status_code, response.text)
        raise HTTPException(502, "Object storage login failed")
    credentials = ET.fromstring(response.text).find(f".//{STS_NAMESPACE}Credentials")
    return tuple(
        credentials.find(f"{STS_NAMESPACE}{key}").text for key in ("AccessKeyId", "SecretAccessKey", "SessionToken")
    )


def get_minio_client(access_token: Optional[str] = Depends(get_access_token)) -> Minio:
    """
    Return a MinIO client acting with the permissions of the given access token.
    """
    if not access_token:
        raise HTTPException(401, "Missing access token")
    access_key, secret_key, session_token = minio_credentials(access_token)
    return Minio(
        get_settings().minio_url,
        access_key=access_key,
        session_token=session_token,
        secret_key=secret_key,
        secure=False,
    )


@functools.lru_cache()
def get_wopi() -> WOPI:
    return WOPI(get_settings().collabora_url + "/hosting/discovery")


def get_username(request: Request, access_token: Optional[str] = Depends(get_access_token)) -> Optional[str]:
    """
    Return the username as in the header x-forwarded-preferred-username.
    If this header does not exist, get the preferred_username from the access token.
    """
    if "x-forwarded-preferred-username" in request.headers:
        return request.headers.get("x-forwarded-preferred-username")
    return token_claims(access_token).get("preferred_username")


def token_claims(access_token: Optional[str]) -> dict:
    if not access_token:
        return {}
    try:
        return jwt.decode(access_token, algorithms=["RS256"], options={"verify_signature": False})
    except jwt.PyJWTError:
        return {}


def project_id_of_bucket(bucket: str) -> Optional[str]:
    if not bucket.startswith(BUCKET_PREFIX):
        return None
    try:
        response = requests.get(f"{get_settings().aii_url}/projects/{bucket.removeprefix(BUCKET_PREFIX)}", timeout=5)
        response.raise_for_status()
        project = response.json()
    except (requests.RequestException, ValueError) as error:
        log.warning("Project of bucket %s could not be resolved: %s", bucket, error)
        return None
    if not isinstance(project, dict) or project.get("s3_bucket") != bucket:
        return None
    return project.get("id")


def can_write(access_token: Optional[str], bucket: str) -> bool:
    policies = token_claims(access_token).get("policy") or []
    if isinstance(policies, str):
        policies = [policies]
    if ADMIN_POLICY in policies:
        return True
    project_id = project_id_of_bucket(bucket)
    return project_id is not None and f"{WRITE_POLICY}_{project_id}" in policies


def parse_project(project_header: Optional[str]) -> dict:
    if not project_header:
        raise HTTPException(400, "Missing Project header")
    try:
        project = json.loads(project_header)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid Project header")
    if not isinstance(project, dict) or not project.get("s3_bucket"):
        raise HTTPException(400, "Invalid Project header")
    return project


def get_project(request: Request) -> dict:
    return parse_project(request.headers.get("Project"))


def get_project_bucket(project: dict = Depends(get_project)) -> str:
    return project["s3_bucket"]
