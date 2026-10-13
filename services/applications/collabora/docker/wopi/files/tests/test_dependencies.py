import jwt
import pytest
import requests
from app import dependencies
from fastapi import HTTPException
from starlette.requests import Request


def make_request(headers=None, query=b""):
    return Request(
        {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
            "query_string": query,
        }
    )


def test_access_token_prefers_the_forwarded_header():
    request = make_request({"x-forwarded-access-token": "forwarded", "authorization": "Bearer bearer"})

    assert dependencies.get_access_token(request) == "forwarded"


def test_access_token_from_the_bearer_header():
    assert dependencies.get_access_token(make_request({"authorization": "Bearer bearer"})) == "bearer"


def test_access_token_from_the_wopi_query_parameter():
    assert dependencies.get_access_token(make_request(query=b"access_token=query")) == "query"


def test_minio_client_requires_a_token():
    with pytest.raises(HTTPException) as error:
        dependencies.get_minio_client(None)
    assert error.value.status_code == 401


class StsResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text
        self.ok = status_code < 400


STS_OK = """<AssumeRoleWithWebIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
<AssumeRoleWithWebIdentityResult><Credentials>
<AccessKeyId>key</AccessKeyId><SecretAccessKey>secret</SecretAccessKey><SessionToken>session</SessionToken>
</Credentials></AssumeRoleWithWebIdentityResult></AssumeRoleWithWebIdentityResponse>"""


def test_minio_credentials_are_assumed_with_the_token(monkeypatch):
    calls = []

    def post(url, params, timeout):
        calls.append(params)
        return StsResponse(200, STS_OK)

    monkeypatch.setattr(dependencies.requests, "post", post)

    assert dependencies.minio_credentials("token") == ("key", "secret", "session")
    assert calls[0]["WebIdentityToken"] == "token"


@pytest.mark.parametrize("status,expected", [(400, 401), (403, 401), (500, 502)])
def test_rejected_minio_login(monkeypatch, status, expected):
    monkeypatch.setattr(dependencies.requests, "post", lambda *a, **k: StsResponse(status))

    with pytest.raises(HTTPException) as error:
        dependencies.minio_credentials("token")
    assert error.value.status_code == expected


def test_unreachable_minio_login(monkeypatch):
    def post(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(dependencies.requests, "post", post)

    with pytest.raises(HTTPException) as error:
        dependencies.minio_credentials("token")
    assert error.value.status_code == 502


def test_username_from_the_token():
    token = jwt.encode({"preferred_username": "kaapana"}, "secret", algorithm="HS256")

    assert dependencies.get_username(make_request(), token) == "kaapana"


def test_username_from_an_invalid_token_is_unknown():
    assert dependencies.get_username(make_request(), "not-a-jwt") is None


PROJECT_ID = "2f0c5a1e-1111-2222-3333-444444444444"


class AiiResponse:
    def __init__(self, status_code, project=None):
        self.status_code = status_code
        self.project = project

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.project


def token_with(policy):
    return jwt.encode({"policy": policy}, "secret", algorithm="HS256")


@pytest.fixture
def aii(monkeypatch):
    calls = []

    def get(url, timeout):
        calls.append(url)
        short_id = url.rsplit("/", 1)[-1]
        if short_id == "2f0c5a1e":
            return AiiResponse(200, {"id": PROJECT_ID, "short_id": short_id, "s3_bucket": f"project-{short_id}"})
        return AiiResponse(404)

    monkeypatch.setattr(dependencies.requests, "get", get)
    return calls


def test_project_admin_policy_can_write(aii):
    assert dependencies.can_write(token_with([f"admin_project_{PROJECT_ID}"]), "project-2f0c5a1e")
    assert aii == ["http://aii.test:8080/projects/2f0c5a1e"]


def test_read_policy_cannot_write(aii):
    assert not dependencies.can_write(token_with([f"read_project_{PROJECT_ID}"]), "project-2f0c5a1e")


def test_admin_policy_of_another_project_cannot_write(aii):
    assert not dependencies.can_write(token_with(["admin_project_99999999-0000"]), "project-2f0c5a1e")


def test_console_admin_can_write_without_asking_aii(aii):
    assert dependencies.can_write(token_with("consoleAdmin"), "project-anything")
    assert aii == []


@pytest.mark.parametrize("bucket", ["project-unknown", "uploads"])
def test_unknown_bucket_cannot_write(aii, bucket):
    assert not dependencies.can_write(token_with([f"admin_project_{PROJECT_ID}"]), bucket)


def test_unreachable_aii_cannot_write(monkeypatch):
    def get(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(dependencies.requests, "get", get)

    assert not dependencies.can_write(token_with([f"admin_project_{PROJECT_ID}"]), "project-2f0c5a1e")


def test_invalid_token_cannot_write(aii):
    assert not dependencies.can_write("not-a-jwt", "project-2f0c5a1e")
