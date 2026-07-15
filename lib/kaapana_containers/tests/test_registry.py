import json
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
