import json
import logging
import os
import re
import sys
import urllib.parse

import httpx
import jwt
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from init import error_page

logging.basicConfig(
    level=logging.INFO,  # Adjust this to INFO or WARNING if you want less verbosity
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Output logs to stdout
)

logger = logging.getLogger(__name__)

app = FastAPI()

# Reused across the auth path of every request; httpx.AsyncClient must not
# serialize the event loop the way blocking `requests` calls would under AII
# or OPA latency.
client = httpx.AsyncClient()


# Matches the platform-wide project URL convention /project/<id>/<service-path>.
# <id> may be the project UUID, the 8-char short_id or the project name — AII's
# GET /projects/{identifier} resolves all three.
PROJECT_PATH_RE = re.compile(r"^/project/([^/]+)(/.*)?$")


def split_project_prefix(requested_prefix: str | None) -> tuple[str | None, str | None]:
    """Split '/project/<id>/rest' into (<id>, '/rest').

    Returns (None, requested_prefix) for unprefixed paths. The rest defaults to
    '/' so OPA policies always see an anchored path.
    """
    if not requested_prefix:
        return None, requested_prefix
    # x-forwarded-uri carries the query string; keep it out of the id match.
    path, sep, query = requested_prefix.partition("?")
    match = PROJECT_PATH_RE.match(path)
    if not match:
        return None, requested_prefix
    return match.group(1), (match.group(2) or "/") + sep + query


async def fetch_project(identifier: str) -> dict | None:
    """Resolve a project via AII; None if it does not exist or is not a project.

    AII has literal sibling routes /projects/rights and /projects/roles that
    return JSON *lists*, so a 2xx alone is not enough: the response must be a
    project object. Validate the shape before it can reach the trusted Project
    header — a Right/Role list or any non-project payload resolves to None,
    treated exactly like not-found: no project is attached and the path stays
    unstripped. That is not a policy deny (see auth_check); the guarantee is the
    missing `Project` header and the 400 the service answers with.
    """
    # Bounded: this runs on the auth path of every project-scoped request, so
    # a hung AII must not hang the whole platform.
    aii_response = await client.get(
        f"http://aii-service.services.svc:8080/projects/{identifier}", timeout=5
    )
    if not aii_response.is_success:
        return None
    project = aii_response.json()
    # id + short_id are sibling computed fields of the AII Project model; their
    # presence distinguishes a real project from a Right/Role list entry.
    if (
        not isinstance(project, dict)
        or "id" not in project
        or "short_id" not in project
    ):
        return None
    return project


async def check_endpoint(input: dict):
    """
    Send the decoded access token and requested prefex to the open policy agent.
    Return the decision of the open policy agent.
    """
    ADMIN_NAMESPACE = os.getenv("ADMIN_NAMESPACE")

    url = f"http://open-policy-agent-service.{ADMIN_NAMESPACE}.svc:8181/v1/data/httpapi/authz/allow"
    r = await client.post(
        url,
        json=input,
        timeout=None,
    )
    try:
        result = r.json()["result"]
    except KeyError as e:
        raise KeyError(f"No result from open policy agent: {e}")
    return result


@app.get("/auth-check")
async def auth_check(request: Request, response: Response):
    """
    Check if the user who made the request is mapped to the required roles in order to be authorized to access the requested resource.
    """

    # Only trust the URI traefik's forwardAuth sets itself: auth-check runs as an
    # *entrypoint* middleware (see the traefik chart's deployment args), so no
    # router middleware has run yet and nothing sets x-forwarded-prefix — only a
    # client could, and a client-supplied value must never influence
    # authorization or project resolution.
    requested_prefix = request.headers.get("x-forwarded-uri")
    access_token = request.headers.get("x-forwarded-access-token", None)
    if access_token is None:
        decoded_access_token = {}
    else:
        decoded_access_token = jwt.decode(
            access_token, options={"verify_signature": False}
        )

    method = request.headers.get("x-forwarded-method")
    input = {
        "input": {
            "access_token": decoded_access_token,
            "requested_prefix": requested_prefix,
            "method": method,
        }
    }
    # The project context comes from the /project/<id>/... URL prefix. It is
    # stripped before policy evaluation so the OPA rules keep matching the
    # plain service paths. An unresolvable id leaves the path UNSTRIPPED and
    # attaches no project, so no `Project` header is set and the service's own
    # `get_project` dependency answers 400. That missing header is what makes
    # it safe -- NOT a policy miss: role `admin`'s catch-all `^/.*` in data.rego
    # matches an unstripped /project/<bogus>/... path just fine. Requests
    # without the prefix fall back to the legacy `Project` cookie (see below).
    #
    # Enrichment from the prefix additionally requires a token. The bare
    # /project/<id> shape normalizes to requested_prefix "/", which
    # auth-policies.rego allows unconditionally, so without this gate an
    # anonymous caller could probe AII for projects on that route. It gates the
    # PREFIX path only -- the cookie branch below is deliberately not token-
    # gated. Anonymous requests reach the gateway solely on oauth2-proxy's
    # skip_auth_routes (^/auth/.*, ^/kaapana-backend/remote/.*,
    # ^/oauth2/metrics$), none of which read the `Project` header.
    #
    # ACCEPTED CONSEQUENCE of that same "/" normalization: an authenticated
    # non-member gets 200 on a bare /project/<foreign-id> where an unprefixed
    # platform answered 403 -- a project-existence oracle over UUIDs, short_ids
    # and project names. Accepted rather than overlooked: every
    # /project/[^/]+/<svc> IngressRoute requires a service segment, so all three
    # normalizing shapes reach only the root `path: /` ingress -- static nginx
    # with no `Project` consumer -- and the enriched header is a forwardAuth
    # *response* header, so it never travels back to the client. Dropping the
    # exemption is not the fix: the shell document is served from that route.
    project_identifier, stripped_prefix = split_project_prefix(requested_prefix)
    try:
        if access_token is not None and project_identifier is not None:
            project = await fetch_project(project_identifier)
            if project is not None:
                # Gateway membership enforcement. Resolving a /project/<id>/
                # scope proves only that the project exists, not that the caller
                # belongs to it -- without this, any authenticated user could
                # scope to any resolvable project and receive the trusted
                # Project header for it. We mirror dicom-web-filter's semantics
                # platform-wide, at the gateway: a non-admin may scope only to
                # projects they are a member of; admins may scope anywhere
                # (downstream services still apply their own read/write rules).
                #
                # This gate is NECESSARY, not sufficient: members/admins fall
                # through to OPA below, which still enforces the per-endpoint
                # claim rules. We only ADD a denial for non-members, never grant.
                #
                # Boundary: enforce on project-scoped SERVICE requests only, not
                # on the bare /project/<id> document, which carries no project
                # data of its own and normalizes to stripped path "/". Scoped
                # SERVICE requests -- everything else under the prefix -- are
                # gated here: a non-member following a foreign deep link gets a
                # hard 403, and downstream services additionally enforce their
                # own read/write checks. No real service path normalizes to bare
                # "/", so it is a clean discriminator.
                #
                # Match by project id: both the resolved project and the token's
                # `projects` claim carry `id` sourced from AII as strings (the
                # token has no short_id, only id/name), so string comparison is
                # robust. Fail closed -- a missing/null/malformed claim yields an
                # empty member set, so a non-admin is denied rather than crashing.
                is_scoped_service_request = stripped_prefix.partition("?")[0] != "/"
                # `roles` must be a list before `in` is applied: on a str it
                # matches substrings ("xadminx"), on a dict it matches keys —
                # either would hand out admin and skip the check below — and a
                # non-dict `realm_access` would raise instead of denying.
                realm_access = decoded_access_token.get("realm_access")
                roles = (
                    realm_access.get("roles")
                    if isinstance(realm_access, dict)
                    else None
                )
                is_admin = isinstance(roles, list) and "admin" in roles
                token_projects = decoded_access_token.get("projects") or []
                if not isinstance(token_projects, list):
                    token_projects = []
                member_ids = {
                    p["id"]
                    for p in token_projects
                    if isinstance(p, dict) and isinstance(p.get("id"), str)
                }
                if (
                    is_scoped_service_request
                    and not is_admin
                    and project.get("id") not in member_ids
                ):
                    message = (
                        f"User is not a member of project {project.get('id')} "
                        f"-> restricting access to {requested_prefix}"
                    )
                    logger.warning(message)
                    return HTMLResponse(
                        content=error_page, status_code=status.HTTP_403_FORBIDDEN
                    )
                input["input"]["project"] = project
                input["input"]["requested_prefix"] = stripped_prefix
        elif project_identifier is None:
            # Legacy fallback for the shipping landing page, which carries the
            # selection in a `Project` cookie while services already read the
            # enriched header. Kept until the UI moves to the URL prefix -- the
            # cookie is what makes unprefixed requests project-scoped today.
            #
            # Deliberately NOT membership-gated, unlike the prefix above: the
            # gate fails closed on a missing `projects` claim, which would deny
            # traffic that works today. A non-member can therefore still scope
            # via the cookie; that residual bypass closes when the cookie
            # derivation goes away with the legacy UI.
            project_cookie = request.cookies.get("Project", None)
            if project_cookie:
                project_id = json.loads(urllib.parse.unquote(project_cookie))["id"]
                project = await fetch_project(project_id)
                if project is not None:
                    input["input"]["project"] = project
    except json.JSONDecodeError as e:
        logger.debug(f"Could not decode the project information from cookies: {e}")
    except httpx.RequestError as e:
        # No enrichment: the path stays unstripped and no project is attached.
        # That is NOT a blanket deny. On the unstripped path `opa eval` measures
        # allow=false for `user` and `project-manager`, so a non-admin's scoped
        # request 403s at OPA -- but role `admin`'s catch-all `^/.*` matches it,
        # so an admin's scoped request proceeds UNSCOPED and the service's own
        # `get_project` answers 400 on the missing `Project` header. On the
        # cookie path the request simply carries no project context, as before.
        # Loud, because an AII outage breaks every project-scoped request.
        logger.warning(f"Could not fetch the project information from aii: {e}")
    except KeyError as e:
        logger.error(f"Could not identify the project: {e}")

    if await check_endpoint(input):
        message = f"Policies satisfied for {method} {requested_prefix} -> ok"
        logger.debug(message)
        response.status_code = status.HTTP_200_OK
        if input["input"].get("project"):
            response.headers["Project"] = json.dumps(input["input"]["project"])
        return message
    else:
        message = f"No policy satisfied -> restricting access to {requested_prefix}"
        logger.warning(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)


@app.get("/opa-bundles/{somedir}/{bundle}")
async def get_opa_bundles(somedir: str, bundle: str):
    """
    Return init data and policies as gzipped tarball.
    """
    f = open(f"/kaapana/app/{somedir}/{bundle}", "rb")
    return StreamingResponse(content=f, media_type="application/octet-stream")
