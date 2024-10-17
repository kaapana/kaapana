from app.kube import get_k8s_secret, hash_secret_name
from google.auth.transport.requests import AuthorizedSession as GoogleAuthorizedSession
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import service_account
from requests import Request


def get_external_session(request: Request) -> str:
    secret_name = hash_secret_name(request.state.endpoint)
    service_account_info = get_k8s_secret(secret_name)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[
            "https://www.googleapis.com/auth/cloud-healthcare",  # read-write
            # "https://www.googleapis.com/auth/cloud-healthcare.dicom.readonly" # read-only
        ],  # TODO maybe scope could be adjusted and limited
    )
    return GoogleAuthorizedSession(credentials=credentials)


async def get_external_token(request: Request) -> str:
    secret_name = hash_secret_name(request.state.endpoint)
    service_account_info = get_k8s_secret(secret_name)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[
            "https://www.googleapis.com/auth/cloud-healthcare",  # read-write
            # "https://www.googleapis.com/auth/cloud-healthcare.dicom.readonly" # read-only
        ],  # TODO maybe scope could be adjusted and limited
    )
    auth_req = GoogleRequest()
    credentials.refresh(auth_req)
    return credentials.token
