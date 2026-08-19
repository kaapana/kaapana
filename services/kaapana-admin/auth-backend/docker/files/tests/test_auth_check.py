"""Seam tests for auth_check, the traefik forwardAuth endpoint.

The AII fetch and OPA call are monkeypatched so no live services are needed;
what is under test is how auth_check wires them together: prefix stripping,
project enrichment, the trusted Project response header, and the security
guards (shape validation, deny-safe fetch failures, auth gating).
"""

import asyncio
import json
import urllib.parse

import jwt
import pytest
from fastapi.testclient import TestClient

import main

PROJECT = {"id": "11111111-2222-3333-4444-555555555555", "short_id": "11111111"}
# Member token: carries PROJECT in its `projects` claim (the AII-sourced shape).
TOKEN = jwt.encode(
    {"sub": "user", "projects": [{"id": PROJECT["id"], "name": "p"}]},
    "secret",
    algorithm="HS256",
)
# Non-member: authenticated, but no matching project membership.
NON_MEMBER_TOKEN = jwt.encode(
    {"sub": "user", "projects": [{"id": "99999999-0000-0000-0000-000000000000"}]},
    "secret",
    algorithm="HS256",
)
ADMIN_TOKEN = jwt.encode(
    {"sub": "admin", "projects": [], "realm_access": {"roles": ["admin"]}},
    "secret",
    algorithm="HS256",
)

client = TestClient(main.app)


@pytest.fixture
def opa_recorder(monkeypatch):
    """Capture the OPA input; default the decision to allow (200)."""
    captured = {}

    async def fake_check_endpoint(input):
        captured["input"] = input["input"]
        return captured.get("decision", True)

    monkeypatch.setattr(main, "check_endpoint", fake_check_endpoint)
    return captured


def _auth_check(uri, *, token=TOKEN, extra_headers=None):
    headers = {"x-forwarded-uri": uri, "x-forwarded-method": "GET"}
    if token is not None:
        headers["x-forwarded-access-token"] = token
    headers.update(extra_headers or {})
    return client.get("/auth-check", headers=headers)


def test_resolved_project_strips_prefix_and_sets_header(monkeypatch, opa_recorder):
    async def fake_fetch(identifier):
        assert identifier == "11111111"
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/project/11111111/data-gallery-ui?limit=10")

    assert resp.status_code == 200
    assert opa_recorder["input"]["requested_prefix"] == "/data-gallery-ui?limit=10"
    assert opa_recorder["input"]["project"] == PROJECT
    # (c) Project header present only when a project was resolved.
    assert json.loads(resp.headers["Project"]) == PROJECT


def test_unresolvable_id_leaves_prefix_unstripped_and_no_header(
    monkeypatch, opa_recorder
):
    # (a) authenticated so the finding-2 gate does not mask the None path:
    # this isolates fetch_project returning None (unknown id).
    async def fake_fetch(identifier):
        return None

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/project/deadbeef/data-gallery-ui")

    assert resp.status_code == 200
    assert (
        opa_recorder["input"]["requested_prefix"] == "/project/deadbeef/data-gallery-ui"
    )
    assert "project" not in opa_recorder["input"]
    assert "Project" not in resp.headers


def test_aii_request_exception_is_deny_safe(monkeypatch, opa_recorder):
    # (b) AII unreachable -> no enrichment; request is still evaluated, and
    # with the path unstripped the (mocked) policy denies -> 403.
    async def boom(identifier):
        raise main.httpx.RequestError("aii down")

    monkeypatch.setattr(main, "fetch_project", boom)
    opa_recorder["decision"] = False

    resp = _auth_check("/project/11111111/data-gallery-ui")

    assert resp.status_code == 403
    assert (
        opa_recorder["input"]["requested_prefix"] == "/project/11111111/data-gallery-ui"
    )
    assert "project" not in opa_recorder["input"]


def test_aii_list_response_is_not_treated_as_project(monkeypatch, opa_recorder):
    # (d) /projects/rights returns a JSON list; the real fetch_project must
    # reject it so no array reaches the trusted Project header.
    class FakeResponse:
        is_success = True

        def json(self):
            return [{"id": 1, "name": "read"}]

    async def fake_get(url, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(main.client, "get", fake_get)

    resp = _auth_check("/project/rights/x")

    assert resp.status_code == 200
    assert opa_recorder["input"]["requested_prefix"] == "/project/rights/x"
    assert "project" not in opa_recorder["input"]
    assert "Project" not in resp.headers


def test_unauthenticated_request_is_not_enriched(monkeypatch, opa_recorder):
    # (e) no token -> enrichment must not run at all (no AII probe, no header).
    called = False

    async def fake_fetch(identifier):
        nonlocal called
        called = True
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/project/11111111/data-gallery-ui", token=None)

    assert resp.status_code == 200
    assert called is False
    assert (
        opa_recorder["input"]["requested_prefix"] == "/project/11111111/data-gallery-ui"
    )
    assert "project" not in opa_recorder["input"]
    assert "Project" not in resp.headers


# --- gateway membership enforcement (finding-3 fix) ---


def test_non_member_scoped_service_request_is_denied(monkeypatch, opa_recorder):
    # Non-admin who is not a member of the resolved project: 403 before OPA,
    # and crucially no Project header leaked in the response.
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/project/11111111/data-gallery-ui", token=NON_MEMBER_TOKEN)

    assert resp.status_code == 403
    assert "Project" not in resp.headers
    # Denied before OPA -> the policy was never consulted.
    assert "input" not in opa_recorder


def test_member_scoped_service_request_is_allowed(monkeypatch, opa_recorder):
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/project/11111111/data-gallery-ui", token=TOKEN)

    assert resp.status_code == 200
    assert opa_recorder["input"]["project"] == PROJECT
    assert json.loads(resp.headers["Project"]) == PROJECT


def test_admin_scoped_to_foreign_project_is_allowed(monkeypatch, opa_recorder):
    # Admin has no membership of PROJECT (empty projects claim) but may scope
    # anywhere; downstream services still apply their own read/write rules.
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/project/11111111/data-gallery-ui", token=ADMIN_TOKEN)

    assert resp.status_code == 200
    assert opa_recorder["input"]["project"] == PROJECT
    assert json.loads(resp.headers["Project"]) == PROJECT


@pytest.mark.parametrize(
    "uri, expected_prefix",
    [
        ("/project/11111111", "/"),  # bare shell document
        ("/project/11111111/", "/"),  # trailing slash
        ("/project/11111111?x=1", "/?x=1"),  # query string
    ],
)
def test_shell_document_route_is_not_membership_gated(
    monkeypatch, opa_recorder, uri, expected_prefix
):
    # The bare /project/<id> SPA shell document carries no project data of its
    # own, so the membership gate skips it: all three shapes normalize to a
    # stripped path of "/" (plus any query) and go on to OPA instead of being
    # 403'd here. There is no soft fallback to the user's own project -- a
    # foreign *deep link* is still denied (see the test below).
    #
    # Scope: this pins the GATE, not the platform. The OPA decision is mocked to
    # allow, and the policy layer does NOT treat the three shapes alike --
    # auth-policies.rego exact-matches `input.requested_prefix == "/"`, so
    # "/?x=1" is denied for `user` and `project-manager` (measured with opa
    # 1.18.2: allow=false; only `admin` passes, via its `^/.*` catch-all). Do
    # not read the third case as "/project/<id>?x=1 works end to end" -- on a
    # live platform it 403s at the policy layer.
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check(uri, token=NON_MEMBER_TOKEN)

    assert resp.status_code == 200
    assert opa_recorder["input"]["requested_prefix"] == expected_prefix


@pytest.mark.parametrize(
    "uri",
    [
        "/project/11111111/datasets",  # shared deep link into a foreign project
        "/project/11111111/datasets/abc",  # nested route
        "/project/11111111/datasets?search=x",  # deep path plus query string
    ],
)
def test_foreign_deep_link_is_denied_for_non_member(monkeypatch, opa_recorder, uri):
    # Counterpart to the bare-shell exemption above: anything *under* the
    # prefix is a scoped request, so a non-member following a shared deep link
    # gets a hard 403 rather than being silently re-scoped. The bare shapes are
    # the only exemption -- a deep path never normalizes to "/".
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check(uri, token=NON_MEMBER_TOKEN)

    assert resp.status_code == 403
    assert "Project" not in resp.headers
    # Denied before OPA -> the policy was never consulted.
    assert "input" not in opa_recorder


@pytest.mark.parametrize(
    "claim",
    [
        {},  # projects key absent
        {"projects": None},  # present but null
        {"projects": "nonsense"},  # present but not a list (iterable str)
        {"projects": 5},  # present but non-iterable
        {"projects": [{"name": "no-id"}]},  # entries missing id
        {"projects": [{"id": ["x"]}]},  # entry id unhashable/non-str
        {"realm_access": None},  # realm_access present but null
        {"realm_access": "nonsense"},  # truthy but not a dict -> would raise
        {"realm_access": 5},  # truthy but not a dict -> would raise
        # `in` on a str matches substrings and on a dict matches keys, so these
        # would each be read as the admin role and skip the gate entirely.
        {"realm_access": {"roles": "admin"}},
        {"realm_access": {"roles": "xadminx"}},
        {"realm_access": {"roles": {"admin": 1}}},
    ],
)
def test_malformed_membership_claim_fails_closed(monkeypatch, opa_recorder, claim):
    # A non-admin whose membership claim is missing/null/malformed is denied on
    # a scoped service request -- fail closed, never crash.
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)
    token = jwt.encode({"sub": "user", **claim}, "secret", algorithm="HS256")

    resp = _auth_check("/project/11111111/data-gallery-ui", token=token)

    assert resp.status_code == 403
    assert "Project" not in resp.headers


# --- legacy `Project` cookie derivation, retained for the shipping UI ---
#
# These pin the standalone-safety premise of the URL-prefix work: unprefixed
# requests must behave exactly as before it. The legacy landing page carries the
# selection in a `Project` cookie while services already read the enriched
# header, so dropping the derivation would unscope every one of them. Delete
# these together with the cookie branch in main.py when the legacy UI goes.


def _cookie_header(value):
    # Sent as a raw Cookie header, the way a browser does; the shared TestClient
    # must not accumulate cookie state between tests.
    return {"cookie": f"Project={value}"}


def _project_cookie(project_id=PROJECT["id"]):
    # Shape the legacy UI writes: URL-encoded JSON with name + id.
    return _cookie_header(
        urllib.parse.quote(json.dumps({"name": "p", "id": project_id}))
    )


def test_legacy_project_cookie_scopes_unprefixed_requests(monkeypatch, opa_recorder):
    seen = {}

    async def fake_fetch(identifier):
        seen["identifier"] = identifier
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check(
        "/kaapana-backend/client/datasets", extra_headers=_project_cookie()
    )

    assert resp.status_code == 200
    assert seen["identifier"] == PROJECT["id"]
    # Path passed through verbatim -- no prefix to strip.
    assert (
        opa_recorder["input"]["requested_prefix"] == "/kaapana-backend/client/datasets"
    )
    assert opa_recorder["input"]["project"] == PROJECT
    assert json.loads(resp.headers["Project"]) == PROJECT


def test_unprefixed_request_without_cookie_carries_no_project(
    monkeypatch, opa_recorder
):
    called = False

    async def fake_fetch(identifier):
        nonlocal called
        called = True
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check("/kaapana-backend/client/datasets")

    assert resp.status_code == 200
    assert called is False
    assert (
        opa_recorder["input"]["requested_prefix"] == "/kaapana-backend/client/datasets"
    )
    assert "project" not in opa_recorder["input"]
    assert "Project" not in resp.headers


def test_legacy_cookie_is_deliberately_not_membership_gated(monkeypatch, opa_recorder):
    # The gate fails closed on a missing `projects` claim, so applying it to the
    # cookie would deny traffic that works today. Consequence, pinned so its
    # removal is a conscious act: a non-member can still scope via the cookie.
    async def fake_fetch(identifier):
        return PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check(
        "/kaapana-backend/client/datasets",
        token=NON_MEMBER_TOKEN,
        extra_headers=_project_cookie(),
    )

    assert resp.status_code == 200
    assert json.loads(resp.headers["Project"]) == PROJECT


@pytest.mark.parametrize(
    "value",
    [
        "not-json",  # JSONDecodeError
        urllib.parse.quote(json.dumps({"name": "p"})),  # KeyError on id
    ],
)
def test_malformed_project_cookie_is_ignored(monkeypatch, opa_recorder, value):
    async def fake_fetch(identifier):
        raise AssertionError("must not resolve a malformed cookie")

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check(
        "/kaapana-backend/client/datasets", extra_headers=_cookie_header(value)
    )

    assert resp.status_code == 200
    assert "project" not in opa_recorder["input"]
    assert "Project" not in resp.headers


# A *different* project, so a cookie-sourced resolution would be visible rather
# than indistinguishable from the URL-prefix one.
COOKIE_PROJECT = {"id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb", "short_id": "77777777"}


@pytest.mark.parametrize(
    "uri, token, identifier, expected_project, expected_status",
    [
        # Resolvable prefix id: the cookie's project must not win.
        ("/project/11111111/datasets", TOKEN, "11111111", PROJECT, 200),
        # Prefix branch attaches nothing (unresolvable id) -- still no cookie
        # fallback, so the request carries no project at all.
        ("/project/deadbeef/datasets", TOKEN, "deadbeef", None, 200),
        # Non-member on a foreign deep link: 403 at the membership gate, and the
        # cookie must not smuggle the scope in behind it.
        ("/project/11111111/datasets", NON_MEMBER_TOKEN, "11111111", None, 403),
    ],
    # The tokens are JWT strings; without ids the test ids are unreadable.
    ids=["member", "unresolvable-prefix-id", "non-member-gated"],
)
def test_url_prefix_takes_precedence_over_the_legacy_cookie(
    monkeypatch, opa_recorder, uri, token, identifier, expected_project, expected_status
):
    # The cookie derivation is an `elif project_identifier is None` fallback, so
    # a request that carries a /project/<id>/ prefix must never consult it -- not
    # even when the prefix resolves to nothing, and not even when the membership
    # gate 403s it. That is what stops the ungated cookie from smuggling a
    # foreign scope past the gate: the gate runs on the prefix id, and no second
    # resolution ever follows.
    seen = []

    async def fake_fetch(ident):
        seen.append(ident)
        if ident == "deadbeef":
            return None
        return COOKIE_PROJECT if ident == COOKIE_PROJECT["id"] else PROJECT

    monkeypatch.setattr(main, "fetch_project", fake_fetch)

    resp = _auth_check(
        uri, token=token, extra_headers=_project_cookie(COOKIE_PROJECT["id"])
    )

    assert resp.status_code == expected_status
    # Exactly one AII resolution, of the URL-prefix id -- never the cookie's.
    assert seen == [identifier]
    if expected_project is None:
        assert "project" not in opa_recorder.get("input", {})
        assert "Project" not in resp.headers
    else:
        assert opa_recorder["input"]["project"] == expected_project
        assert json.loads(resp.headers["Project"]) == expected_project


def test_client_supplied_x_forwarded_prefix_is_ignored(monkeypatch, opa_recorder):
    # auth-check runs as an entrypoint middleware, so traefik never sets
    # x-forwarded-prefix -- only a client can. Honouring it would let a caller
    # substitute "/" (allowed unconditionally by the policy) for the real path.
    resp = _auth_check(
        "/kaapana-backend/client/datasets", extra_headers={"x-forwarded-prefix": "/"}
    )

    assert resp.status_code == 200
    assert (
        opa_recorder["input"]["requested_prefix"] == "/kaapana-backend/client/datasets"
    )


# --- fetch_project shape validation (the finding-1 fix), tested directly ---


class _Resp:
    def __init__(self, payload, is_success=True):
        self._payload = payload
        self.is_success = is_success

    def json(self):
        return self._payload


@pytest.mark.parametrize(
    "payload, is_success, expected",
    [
        (PROJECT, True, PROJECT),  # real project object
        ([{"id": 1}], True, None),  # rights/roles list shape
        ({"detail": "nope"}, True, None),  # dict without id/short_id
        ({"id": "x"}, True, None),  # missing short_id
        (PROJECT, False, None),  # non-2xx
    ],
)
def test_fetch_project_shape_validation(monkeypatch, payload, is_success, expected):
    async def fake_get(url, timeout=None):
        return _Resp(payload, is_success=is_success)

    monkeypatch.setattr(main.client, "get", fake_get)

    result = asyncio.run(main.fetch_project("someid"))
    assert result == expected
