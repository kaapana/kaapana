import hashlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from kaapana_containers.registries.registry import OCIError, OCIRegistryDiscovery


@pytest.fixture
def client():
    c = OCIRegistryDiscovery(
        "https://registry.example.com",
        "user/repo",
        username="user",
        password="pass",
    )
    c._request_with_auth_retry = AsyncMock()
    return c


def _mock_response(status_code: int, body: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_error = status_code >= 400
    resp.text = text
    resp.json.return_value = body or {}
    return resp


# ---------------------------------------------------------------------------
# OCIError
# ---------------------------------------------------------------------------

class TestOCIError:
    def test_str_with_code(self):
        assert str(OCIError("not found", code="NAME_UNKNOWN")) == "NAME_UNKNOWN: not found"

    def test_str_without_code(self):
        assert str(OCIError("generic error")) == "generic error"

    def test_from_response_parses_oci_body(self):
        resp = _mock_response(
            404,
            body={"errors": [{"code": "NAME_UNKNOWN", "message": "repository not found"}]},
        )
        err = OCIError.from_response(resp)
        assert err.code == "NAME_UNKNOWN"
        assert "repository not found" in str(err)

    def test_from_response_with_detail(self):
        resp = _mock_response(
            401,
            body={"errors": [{"code": "UNAUTHORIZED", "message": "auth required", "detail": "token expired"}]},
        )
        err = OCIError.from_response(resp)
        assert err.code == "UNAUTHORIZED"
        assert "token expired" in str(err)

    def test_from_response_fallback_to_http_status(self):
        resp = _mock_response(500, text="Internal Server Error")
        err = OCIError.from_response(resp)
        assert err.code is None
        assert "500" in str(err)

    def test_from_response_no_errors_array(self):
        resp = _mock_response(400, body={})
        err = OCIError.from_response(resp)
        assert "400" in str(err)


# ---------------------------------------------------------------------------
# check_login
# ---------------------------------------------------------------------------

class TestCheckLogin:
    async def test_success_returns_true(self, client):
        client._request_with_auth_retry.return_value = _mock_response(200)
        assert await client.check_login() is True

    async def test_unauthorized_raises(self, client):
        client._request_with_auth_retry.side_effect = OCIError(
            "auth required", code="UNAUTHORIZED"
        )
        with pytest.raises(OCIError) as exc_info:
            await client.check_login()
        assert exc_info.value.code == "UNAUTHORIZED"

    async def test_denied_raises(self, client):
        client._request_with_auth_retry.side_effect = OCIError("denied", code="DENIED")
        with pytest.raises(OCIError) as exc_info:
            await client.check_login()
        assert exc_info.value.code == "DENIED"


# ---------------------------------------------------------------------------
# list_tags
# ---------------------------------------------------------------------------

class TestListTags:
    async def test_returns_tag_list(self, client):
        client._request_with_auth_retry.return_value = _mock_response(
            200, body={"tags": ["v1.0.0", "v2.0.0"]}
        )
        assert await client.list_tags() == ["v1.0.0", "v2.0.0"]

    async def test_empty_repository_returns_empty_list(self, client):
        client._request_with_auth_retry.return_value = _mock_response(
            200, body={"tags": None}
        )
        assert await client.list_tags() == []

    async def test_name_unknown_propagates(self, client):
        client._request_with_auth_retry.side_effect = OCIError(
            "repository not found", code="NAME_UNKNOWN"
        )
        with pytest.raises(OCIError) as exc_info:
            await client.list_tags()
        assert exc_info.value.code == "NAME_UNKNOWN"

    async def test_other_oci_error_propagates(self, client):
        client._request_with_auth_retry.side_effect = OCIError(
            "server error", code="INTERNAL_ERROR"
        )
        with pytest.raises(OCIError, match="server error"):
            await client.list_tags()


# ---------------------------------------------------------------------------
# client_options
# ---------------------------------------------------------------------------

class TestClientOptions:
    async def test_default_options_are_retained(self, client):
        async with client:
            assert client._client is not None
            assert client._client.timeout.read == 5.0
            assert client._client.timeout.write == 5.0
            assert client._client.timeout.connect == 5.0
            assert client._client.timeout.pool == 5.0



    async def test_options_forwarded_to_httpx_client(self):
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={"timeout": 60.0},
        )

        async with client:
            assert client._client is not None
            assert client._client.timeout.read == 60.0
            assert client._client.timeout.write == 60.0
            assert client._client.timeout.connect == 60.0
            assert client._client.timeout.pool == 60.0


# ---------------------------------------------------------------------------
# Harbor session-cookie / CSRF behavior
#
# Harbor sets a session cookie (sid) on every response - including the 401 that
# starts the bearer-token flow - and enforces browser CSRF rules on any unsafe
# /v2/ request that carries it (csrfSkipper in Harbor's csrf middleware only
# skips /v2/ requests without a session). A client that persists cookies
# therefore has every POST/PUT after the first response rejected with
# "FORBIDDEN: CSRF token invalid". The transport below mimics exactly that.
# ---------------------------------------------------------------------------

class _MockHarbor:
    """Harbor-like transport handler: cookie on every response, CSRF on unsafe
    requests that carry one, bearer-token auth flow, blob upload endpoints."""

    def __init__(self):
        self.blobs: dict = {}
        self.manifests: dict = {}
        self.requests: list[httpx.Request] = []
        self._sid = 0

    def _headers(self) -> dict:
        self._sid += 1
        return {"Set-Cookie": f"sid=session-{self._sid}; Path=/; HttpOnly"}

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        headers = self._headers()

        if "Cookie" in request.headers and request.method not in ("GET", "HEAD"):
            return httpx.Response(
                403,
                headers=headers,
                json={"errors": [{"code": "FORBIDDEN", "message": "CSRF token invalid"}]},
            )

        if request.url.path == "/service/token":
            return httpx.Response(200, headers=headers, json={"token": "test-bearer"})

        # Like real Harbor, /v2/ accepts only bearer tokens; basic credentials get
        # the 401 + WWW-Authenticate that starts the token flow. This makes every
        # upload exercise the 401 retry, including the re-sent request body.
        if not request.headers.get("Authorization", "").startswith("Bearer "):
            headers["WWW-Authenticate"] = (
                'Bearer realm="https://registry.example.com/service/token",'
                'service="harbor-registry"'
            )
            return httpx.Response(401, headers=headers)

        if request.method == "POST" and request.url.path.endswith("/blobs/uploads/"):
            return httpx.Response(
                202,
                headers={**headers, "Location": "/v2/user/repo/blobs/uploads/uuid-1?_state=x"},
            )

        if request.method == "PUT" and "/blobs/uploads/" in request.url.path:
            body = await request.aread()
            digest = request.url.params.get("digest")
            self.blobs[digest] = body
            return httpx.Response(201, headers=headers)

        if request.method == "PUT" and "/manifests/" in request.url.path:
            self.manifests[request.url.path.rsplit("/", 1)[-1]] = await request.aread()
            return httpx.Response(201, headers=headers)

        return httpx.Response(404, headers=headers)


@pytest.fixture
def harbor():
    return _MockHarbor()


@pytest.fixture
def harbor_client(harbor):
    return OCIRegistryDiscovery(
        "https://registry.example.com",
        "user/repo",
        username="user",
        password="pass",
        client_options={"transport": httpx.MockTransport(harbor)},
    )


class TestNoCookiePersistence:
    async def test_client_never_sends_cookies(self, harbor, harbor_client):
        async with harbor_client as client:
            await client._upload_blob(b"payload", "application/octet-stream")
        assert all("Cookie" not in r.headers for r in harbor.requests)

    async def test_create_or_update_tag_succeeds_against_cookie_setting_registry(
        self, harbor, harbor_client, tmp_path
    ):
        # End-to-end regression for the offline-installer publish: multiple
        # sequential uploads plus the manifest PUT, each preceded by responses
        # that all try to set a session cookie.
        f = tmp_path / "installer.tar.gz"
        f.write_bytes(b"tarball-bytes")
        async with harbor_client as client:
            assert await client.create_or_update_tag(
                tag="0.0.1",
                user_metadata={"kind": "test"},
                files=[f.name],
                base_dir=str(tmp_path),
            )
        assert b"tarball-bytes" in harbor.blobs.values()
        assert "0.0.1" in harbor.manifests

    async def test_cookie_jar_would_break_upload(self, harbor):
        # Sanity check that the mock enforces Harbor's behavior: with cookie
        # persistence re-enabled, the upload PUT is rejected as CSRF.
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            username="user",
            password="pass",
            client_options={
                "transport": httpx.MockTransport(harbor),
                "cookies": httpx.Cookies(),
            },
        )
        async with client:
            with pytest.raises(OCIError, match="CSRF token invalid"):
                await client._upload_blob(b"payload", "application/octet-stream")


class TestStreamingFileUpload:
    async def test_upload_file_streams_and_reports_digest_and_size(
        self, harbor, harbor_client, tmp_path
    ):
        payload = b"x" * (3 * 1024 * 1024 + 17)  # spans several stream chunks
        f = tmp_path / "blob.bin"
        f.write_bytes(payload)
        async with harbor_client as client:
            meta = await client._upload_file(str(f), stored_name="blob.bin")
        expected_digest = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        assert meta["digest"] == expected_digest
        assert meta["size"] == len(payload)
        assert harbor.blobs[expected_digest] == payload
        # the streamed PUT must declare its length instead of chunking
        file_put = next(
            r for r in harbor.requests
            if r.method == "PUT" and r.url.params.get("digest") == expected_digest
        )
        assert file_put.headers["Content-Length"] == str(len(payload))
        assert "transfer-encoding" not in file_put.headers

    async def test_streamed_body_survives_401_auth_retry(self, tmp_path):
        # A 401 on the PUT itself (e.g. an expired token) forces a second attempt;
        # a one-shot stream would arrive empty or raise StreamConsumed there, so
        # both attempts must carry the complete body.
        put_bodies = []

        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/service/token":
                return httpx.Response(200, json={"token": "fresh-token"})
            if request.method == "POST":
                return httpx.Response(
                    202, headers={"Location": "/v2/user/repo/blobs/uploads/u1"}
                )
            if request.method == "PUT":
                put_bodies.append(await request.aread())
                if len(put_bodies) == 1:
                    return httpx.Response(
                        401,
                        headers={
                            "WWW-Authenticate": 'Bearer realm="https://registry.example.com/service/token",service="harbor-registry"'
                        },
                    )
                return httpx.Response(201)
            return httpx.Response(404)

        payload = b"y" * (2 * 1024 * 1024 + 5)
        f = tmp_path / "blob.bin"
        f.write_bytes(payload)
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            username="user",
            password="pass",
            client_options={"transport": httpx.MockTransport(handler)},
        )
        async with client:
            await client._upload_file(str(f))
        assert put_bodies == [payload, payload]


class TestRedirectFollowing:
    async def test_blob_download_follows_redirect(self):
        # Registries commonly answer blob GETs with a 307 to object storage.
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "storage.example.com":
                return httpx.Response(200, content=b"blob-content")
            if "/blobs/sha256:" in request.url.path:
                return httpx.Response(
                    307, headers={"Location": "https://storage.example.com/obj"}
                )
            return httpx.Response(404)

        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={"transport": httpx.MockTransport(handler)},
        )
        async with client:
            data = await client._download_blob("sha256:" + "a" * 64)
        assert data == b"blob-content"
