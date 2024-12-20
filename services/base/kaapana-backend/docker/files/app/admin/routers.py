import json
import uuid
from datetime import datetime, timezone

import jwt
import requests
from app.config import settings
from app.dependencies import get_minio, get_opensearch
from app.workflows.utils import raise_kaapana_connection_error, requests_retry_session
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from minio.error import S3Error
from starlette.responses import StreamingResponse

DEFAULT_STATIC_WEBSITE_BUCKET = "staticwebsiteresults"

router = APIRouter()


@router.get("/")
async def root(request: Request):
    return {
        "message": "Welcome to the backend",
        "root_path": request.scope.get("root_path"),
    }


@router.get("/health-check")
def health_check():
    return {f"Kaapana backend is up and running!"}


@router.get("/get-static-website-results-html")
def get_static_website_results_html(
    request: Request,
    minioClient=Depends(get_minio),
) -> StreamingResponse:
    """Get the html file from the static website results bucket.

    Args:
        request (Request): Request object.
        minioClient (minio.Minio): Minio client.

    Raises:
        HTTPException: If object_name query parameter is not provided.
        HTTPException: If object is not found in the bucket.

    Returns:
        StreamingResponse: Streaming response of the html file.
    """
    # Retrieve the object name from query parameters
    object_name = request.query_params.get("object_name")
    if not object_name:
        raise HTTPException(
            status_code=400, detail="object_name query parameter is required."
        )

    # set the bucket_name automatically from the request header
    bucket_name: str = (DEFAULT_STATIC_WEBSITE_BUCKET,)
    project = json.loads(request.headers.get("project"))
    if project and "s3_bucket" in project:
        bucket_name = project.get("s3_bucket")

    try:
        html_file = minioClient.get_object(bucket_name, object_name)
    except S3Error:
        raise HTTPException(status_code=404, detail="Object not found in the bucket.")

    return StreamingResponse(html_file, media_type="text/html")


@router.get("/get-static-website-results")
def get_static_website_results(
    request: Request,
    minioClient=Depends(get_minio),
):
    # set the bucket_name automatically from the request header
    bucket_name: str = (DEFAULT_STATIC_WEBSITE_BUCKET,)
    project = json.loads(request.headers.get("project"))
    if project and "s3_bucket" in project:
        bucket_name = project.get("s3_bucket")

    def build_tree(item, filepath, org_filepath):
        # Adapted from https://stackoverflow.com/questions/8484943/construct-a-tree-from-list-os-file-paths-python-performance-dependent
        splits = filepath.split("/", 1)
        if len(splits) == 1:
            item["vuetifyFiles"].append(
                {
                    "name": splits[0],
                    "file": "html",
                    "path": f"/kaapana-backend/get-static-website-results-html?object_name={org_filepath}",
                }
            )
        else:
            parent_folder, filepath = splits
            if parent_folder not in item:
                item[parent_folder] = {"vuetifyFiles": []}
            build_tree(item[parent_folder], filepath, org_filepath)

    def _get_vuetify_tree_structure(tree):
        subtree = []
        for parent, children in tree.items():
            # print(parent, children)
            if parent == "vuetifyFiles":
                subtree = children
            else:
                subtree.append(
                    {
                        "name": parent,
                        "path": str(uuid.uuid4()),
                        "children": _get_vuetify_tree_structure(children),
                    }
                )
        return subtree

    # if bucket is not the default static website bucket,
    # fetch all the static websites from the directory with the `staticwebsiteresults`
    # directory inside project bucket.
    prefix = None
    if bucket_name != DEFAULT_STATIC_WEBSITE_BUCKET:
        prefix = DEFAULT_STATIC_WEBSITE_BUCKET

    tree = {"vuetifyFiles": []}

    try:
        objects = minioClient.list_objects(bucket_name, prefix=prefix, recursive=True)
        for obj in objects:
            if obj.object_name.endswith("html") and obj.object_name != "index.html":
                build_tree(tree, obj.object_name, obj.object_name)
        return _get_vuetify_tree_structure(tree)
    except S3Error:
        raise HTTPException(
            status_code=404,
            detail="Bucket name not found or Dont have access to the bucket",
        )


@router.get("/get-os-dashboards")
def get_os_dashboards(os_client=Depends(get_opensearch)):
    try:
        res = os_client.search(
            body={
                "query": {"exists": {"field": "dashboard"}},
                "_source": ["dashboard.title"],
            },
            size=10000,
            from_=0,
        )
    except Exception as e:
        print("ERROR in OpenSearch search!")
        return {"Error message": str(e)}, 500

    hits = res["hits"]["hits"]
    dashboards = list(sorted([hit["_source"]["dashboard"]["title"] for hit in hits]))
    return {"dashboards": dashboards}


@router.get("/get-traefik-routes")
def get_traefik_routes():
    try:
        with requests.Session() as s:
            r = requests_retry_session(session=s).get(
                f"{settings.traefik_url}/api/http/routers"
            )
        raise_kaapana_connection_error(r)
        return r.json()
    except Exception as e:
        print("ERROR in getting traefik routes!")
        return {"Error message": str(e)}, 500


@router.get("/open-policy-data")
def get_open_policy_data():
    r = requests.get(
        f"http://open-policy-agent-service.{settings.admin_namespace}.svc:8181/v1/data/httpapi/authz"
    )
    return r.json().get("result")


@router.get("/oidc-logout")
def oidc_logout(request: Request):
    """
    Delete the keycloak session corresponding to the session of the access token in the request.
    Response with a redirect to oauth2-proxy browser session logout url.
    """

    def _get_access_token(
        username: str,
        password: str,
        client_id: str,
    ):
        """
        Get access token for the admin keycloak user.
        """
        payload = {
            "username": username,
            "password": password,
            "client_id": client_id,
            "grant_type": "password",
        }
        r = requests.post(
            f"{settings.keycloak_url}/auth/realms/master/protocol/openid-connect/token",
            verify="/etc/certs/kaapana.pem",
            data=payload,
        )
        r.raise_for_status()
        return r.json()["access_token"]

    access_token = request.headers.get("x-forwarded-access-token")
    decoded_access_token = jwt.decode(access_token, options={"verify_signature": False})
    token_session_id = decoded_access_token.get("sid")
    assert token_session_id, "Session id could not be determined from access token"
    user_id = decoded_access_token.get("sub")

    keycloak_admin_access_token = _get_access_token(
        settings.keycloak_admin_username,
        settings.keycloak_admin_password,
        "admin-cli",
    )
    security_headers = {"Authorization": f"Bearer {keycloak_admin_access_token}"}

    response_sessions = requests.get(
        f"{settings.keycloak_url}/auth/admin/realms/kaapana/users/{user_id}/sessions",
        verify="/etc/certs/kaapana.pem",
        headers=security_headers,
    )

    user_sessions = response_sessions.json()

    ### Remove the session that corresponds to the access token from keycloak if the session exists
    for user_session in user_sessions:
        user_session_id = user_session.get("id")
        if user_session.get("id") == token_session_id:
            r = requests.delete(
                f"{settings.keycloak_url}/auth/admin/realms/kaapana/sessions/{token_session_id}",
                headers=security_headers,
                verify="/etc/certs/kaapana.pem",
            )
            r.raise_for_status()
            break
    response = RedirectResponse("/oauth2/sign_out?rd=/")
    ### Delete the token cookie for the minio session.
    response.set_cookie(
        key="token", value="", expires=datetime(1900, 1, 1, tzinfo=timezone.utc)
    )
    ### Delete the session cookies for the opensearch session: https://opensearch.org/docs/latest/security/authentication-backends/openid-connect/#session-management-with-additional-cookies
    for cookie in [
        "security_authentication",
        "security_authentication_oidc1",
        "security_authentication_oidc2",
        "security_authentication_oidc3",
    ]:
        response.set_cookie(
            key=cookie,
            value="",
            max_age=0,
            path="/meta",
            expires=datetime(1900, 1, 1, tzinfo=timezone.utc),
        )

    return response
