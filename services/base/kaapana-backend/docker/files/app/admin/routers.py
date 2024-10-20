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

    # Bucket name
    bucket = "staticwebsiteresults"

    try:
        html_file = minioClient.get_object(bucket, object_name)
    except S3Error:
        raise HTTPException(status_code=404, detail="Object not found in the bucket.")

    return StreamingResponse(html_file, media_type="text/html")


@router.get("/get-static-website-results")
def get_static_website_results(
    request: Request,
    minioClient=Depends(get_minio),
):
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
            print(parent, children)
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

    tree = {"vuetifyFiles": []}
    objects = minioClient.list_objects(
        "staticwebsiteresults", prefix=None, recursive=True
    )
    for obj in objects:
        if obj.object_name.endswith("html") and obj.object_name != "index.html":
            build_tree(tree, obj.object_name, obj.object_name)
    return _get_vuetify_tree_structure(tree)


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

    def get_access_token(
        username: str,
        password: str,
        ssl_check: bool,
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
            verify=ssl_check,
            data=payload,
        )
        r.raise_for_status()
        return r.json()["access_token"]

    access_token = request.headers.get("x-forwarded-access-token")
    decoded_access_token = jwt.decode(access_token, options={"verify_signature": False})
    session_state = decoded_access_token.get("session_state")
    user_id = decoded_access_token.get("sub")

    keycloak_admin_access_token = get_access_token(
        settings.keycloak_admin_username,
        settings.keycloak_admin_password,
        False,
        "admin-cli",
    )
    security_headers = {"Authorization": f"Bearer {keycloak_admin_access_token}"}

    user_sessions = requests.get(
        f"{settings.keycloak_url}/auth/admin/realms/kaapana/users/{user_id}/sessions",
        verify=False,
        headers=security_headers,
    ).json()

    ### Remove the session that corresponds to the access token from keycloak if the session exists
    for user_session in user_sessions:
        if user_session.get("id") == session_state:
            r = requests.delete(
                f"{settings.keycloak_url}/auth/admin/realms/kaapana/sessions/{session_state}",
                headers=security_headers,
                verify=False,
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
