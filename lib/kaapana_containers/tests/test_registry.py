import hashlib
import json
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

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
# finalize timeout
# ---------------------------------------------------------------------------


def _upload_timeouts_handler(timeouts: list[tuple[str, dict]]):
    def handler(request: httpx.Request) -> httpx.Response:
        timeouts.append((request.method, request.extensions["timeout"]))
        if request.method == "HEAD":
            return httpx.Response(404)
        if request.method in ("POST", "PATCH"):
            return httpx.Response(
                202, headers={"location": "/v2/user/repo/blobs/uploads/u1"}
            )
        return httpx.Response(201)

    return handler


class TestFinalizeTimeout:
    async def test_only_the_closing_put_waits_longer(self, tmp_path):
        (tmp_path / "a.bin").write_bytes(b"content")
        timeouts: list[tuple[str, dict]] = []
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={
                "timeout": 60.0,
                "transport": httpx.MockTransport(_upload_timeouts_handler(timeouts)),
            },
        )

        async with client:
            await client._upload_file(str(tmp_path / "a.bin"), "a.bin")

        default = {"connect": 60.0, "read": 60.0, "write": 60.0, "pool": 60.0}
        *others, closing = timeouts
        assert closing == ("PUT", {**default, "read": 1800.0})
        assert others and all(timeout == default for _, timeout in others)

    @pytest.mark.parametrize("client_timeout", [3600.0, None])
    async def test_longer_client_read_timeout_is_kept(self, tmp_path, client_timeout):
        (tmp_path / "a.bin").write_bytes(b"content")
        timeouts: list[tuple[str, dict]] = []
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={
                "timeout": client_timeout,
                "transport": httpx.MockTransport(_upload_timeouts_handler(timeouts)),
            },
        )

        async with client:
            await client._upload_file(str(tmp_path / "a.bin"), "a.bin")

        assert timeouts[-1][0] == "PUT"
        assert timeouts[-1][1]["read"] == client_timeout

    async def test_none_waits_without_limit(self, tmp_path):
        (tmp_path / "a.bin").write_bytes(b"content")
        timeouts: list[tuple[str, dict]] = []
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={
                "transport": httpx.MockTransport(_upload_timeouts_handler(timeouts))
            },
            finalize_timeout=None,
        )

        async with client:
            await client._upload_file(str(tmp_path / "a.bin"), "a.bin")

        assert timeouts[-1][0] == "PUT"
        assert timeouts[-1][1]["read"] is None


# ---------------------------------------------------------------------------
# cookies
# ---------------------------------------------------------------------------


def _session_cookie_handler(seen: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        headers = {"set-cookie": "sid=abc; Path=/"}
        if request.url.path == "/token":
            return httpx.Response(200, headers=headers, json={"token": "t"})
        if request.headers.get("authorization") != "Bearer t":
            headers["www-authenticate"] = (
                'Bearer realm="https://registry.example.com/token",'
                'service="registry.example.com"'
            )
            return httpx.Response(401, headers=headers)
        if request.url.path.endswith("/tags/list"):
            return httpx.Response(200, headers=headers, json={"tags": ["v1.0.0"]})
        return httpx.Response(200, headers=headers)

    return handler


class TestCookies:
    async def test_never_sends_cookies_set_by_registry(self):
        seen: list[httpx.Request] = []
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            username="user",
            password="pass",
            client_options={
                "transport": httpx.MockTransport(_session_cookie_handler(seen))
            },
        )

        async with client:
            assert await client.check_login() is True
            assert await client.list_tags() == ["v1.0.0"]

        assert len(seen) == 4
        assert [r.headers.get("cookie") for r in seen] == [None] * len(seen)

    async def test_cookies_option_is_rejected(self):
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={"cookies": {"sid": "abc"}},
        )

        with pytest.raises(TypeError):
            async with client:
                pass


# ---------------------------------------------------------------------------
# redirects
# ---------------------------------------------------------------------------


def _redirecting_blob_handler(
    seen: list[httpx.Request], blobs: dict[str, bytes], manifest: dict
):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if request.url.host == "storage.example.com":
            return httpx.Response(200, content=blobs[path.rsplit("/", 1)[-1]])
        if "/manifests/" in path:
            return httpx.Response(200, json=manifest)
        if "/blobs/" in path:
            digest = path.rsplit("/", 1)[-1]
            return httpx.Response(
                307, headers={"location": f"https://storage.example.com/{digest}"}
            )
        return httpx.Response(404)

    return handler


class TestRedirects:
    async def test_follows_blob_redirect_without_forwarding_credentials(self, tmp_path):
        payload = b"file content"
        payload_digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        config = json.dumps(
            {"files": [{"filename": "a.bin", "digest": payload_digest}]}
        ).encode()
        config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
        manifest = {
            "schemaVersion": 2,
            "config": {"digest": config_digest},
            "layers": [],
        }
        seen: list[httpx.Request] = []
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            username="user",
            password="pass",
            client_options={
                "transport": httpx.MockTransport(
                    _redirecting_blob_handler(
                        seen, {config_digest: config, payload_digest: payload}, manifest
                    )
                )
            },
        )

        async with client:
            assert await client.download_files("v1", str(tmp_path)) is True

        assert (tmp_path / "a.bin").read_bytes() == payload
        storage = [r for r in seen if r.url.host == "storage.example.com"]
        registry = [r for r in seen if r.url.host == "registry.example.com"]
        assert len(storage) == 2
        assert all("authorization" not in r.headers for r in storage)
        assert all(r.headers["authorization"].startswith("Basic ") for r in registry)

    @pytest.mark.parametrize(
        "target",
        [
            "https://storage.example.com/blob",
            "https://registry.example.com:8443/blob",
            "http://registry.example.com/blob",
        ],
    )
    async def test_challenge_from_redirect_target_gets_no_credentials(self, target):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if str(request.url) == target:
                return httpx.Response(
                    401,
                    headers={
                        "www-authenticate": 'Bearer realm="https://evil.example.com/token",service="evil"'
                    },
                )
            return httpx.Response(307, headers={"location": target})

        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            username="user",
            password="pass",
            client_options={"transport": httpx.MockTransport(handler)},
        )

        async with client:
            with pytest.raises(OCIError):
                await client.list_tags()

        assert [str(r.url) for r in seen][1:] == [target]
        assert "authorization" not in seen[1].headers

    async def test_follow_redirects_option_is_rejected(self):
        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={"follow_redirects": False},
        )

        with pytest.raises(TypeError):
            async with client:
                pass

    async def test_token_request_follows_redirects(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/token":
                return httpx.Response(307, headers={"location": "/token2"})
            if request.url.path == "/token2":
                return httpx.Response(200, json={"token": "t"})
            if request.headers.get("authorization") == "Bearer t":
                return httpx.Response(200, json={"tags": ["v1"]})
            return httpx.Response(
                401,
                headers={
                    "www-authenticate": 'Bearer realm="https://registry.example.com/token",service="registry.example.com"'
                },
            )

        client = OCIRegistryDiscovery(
            "https://registry.example.com",
            "user/repo",
            client_options={"transport": httpx.MockTransport(handler)},
        )

        async with client:
            assert await client.list_tags() == ["v1"]
