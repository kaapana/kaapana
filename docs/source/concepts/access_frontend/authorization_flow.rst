.. _concepts_authorization_flow:

Authorization Flow
####################

Every request to Kaapana, whether a browser loading the landing page or a script calling an API, passes through the same chain of components before it reaches a backend service.
This page explains how that chain authenticates a user, decides what they are allowed to do, and where the current design still has rough edges.

Authentication vs. authorization
===================================

**Authentication** identifies who is making a request; **authorization** decides what they are allowed to do with it.
Authentication has to happen first -- an authorization decision is meaningless without an identity to evaluate it against.

Kaapana's authentication is standardized on **OAuth2** and its identity layer, **OpenID Connect (OIDC)**: a client proves it acts on behalf of a user to an **Identity Provider (IdP)**, which returns a **JSON Web Token (JWT)** describing that user (claims such as username, roles, and scopes).

The players
=============

* **Keycloak** -- the Identity Provider. Issues and validates tokens, and (see :ref:`Keycloak user groups<keycloak_groups>`) maps users onto the ``user``, ``project-manager`` and ``admin`` roles that the rest of the platform authorizes against.
* **OAuth2-Proxy** -- sits in front of the platform as the browser-facing login gate; it drives the *Authorization Code Grant* against Keycloak and turns a successful login into a session cookie.
* **Traefik** -- the internal reverse proxy and ingress in front of every cluster service.

Current flow
==============

.. mermaid::

    sequenceDiagram
        participant B as Browser
        participant O as OAuth2-Proxy
        participant T as Traefik
        participant K as Keycloak (IdP)
        participant A as AII (Access Information Interface)
        participant F as Auth Backend
        participant P as OPA
        participant S as Backend Service

        alt User requests HTTP
            B->>T: HTTP Request
            T-->>B: Redirect to HTTPS
        end

        B->>O: HTTPS Request

        alt Authorization Code Grant (first visit)
            O-->>B: Redirect to Keycloak Login
            B->>O: Login at Keycloak (user credentials)
            O->>T: Proxy to upstream
            T->>K: Proxy to Keycloak
            K->>A: Fetch user attributes for claim enrichment
            A-->>K: User info / access metadata
            K-->>B: Authorization code + redirect
            B->>O: Authorization code
            O->>K: Token exchange
            K-->>O: Access token / claims
            O-->>B: Set session cookie
        end

        B->>O: Request with session cookie (URL may carry a /project/id prefix)
        O->>T: Forward + x-forwarded headers
        T->>F: ForwardAuth check (headers, path)

        alt URL carries a /project/id prefix
            F->>A: Fetch project resource (short_id, UUID or name)
            A-->>F: Project details (JSON)
            F->>F: Membership gate against the token's projects claim
        end

        F->>P: Evaluate policy (user, project, resource)

        alt denied
            P-->>F: Deny
            F-->>T: 403
            T-->>O: 403 Forbidden
            O-->>B: 403
        else allowed
            P-->>F: Allow
            F-->>T: 200 OK + Project header
            T->>S: Forward request + Project header
            S-->>T: Response
            T-->>O: Response
            O-->>B: Response
        end

Four things happen, in order, on every authenticated request:

#. **Authentication at the edge.** OAuth2-Proxy terminates the Authorization Code Grant with Keycloak and reduces the result to a session cookie -- everything after this step works with the cookie, not with Keycloak directly.
#. **Claim enrichment.** During login, Keycloak calls the **Access Information Interface (AII)** to attach project- and role-related attributes to the token as claims, rather than each backend service looking them up independently.
#. **Policy enforcement at Traefik.** Traefik acts as the **Policy Enforcement Point (PEP)**: it forwards every request to an **Auth Backend**, which decodes the token, fetches project details from the AII when the requested URL carries a ``/project/<short_id>/`` prefix (and refuses the request unless the caller is a member of that project), and asks the **Open Policy Agent (OPA)** -- the **Policy Decision Point (PDP)** -- for an allow/deny decision.
#. **Header-based trust downstream.** Once allowed, Traefik attaches the resolved project (and other claims) as headers on the forwarded request; backend services trust these headers rather than re-deriving them.

.. important::
   The web interface -- and any authorization decision that depends on a project -- only works correctly once a :term:`project` is selected, because the ``/project/<short_id>/`` URL prefix that selection produces is what triggers step 3's project-scoped policy evaluation. A request without the prefix carries no project context at all: project-requiring endpoints answer **400**. See :doc:`../../development_guide/preview/project_scoping` for the mechanism.

Known limitations of this design
===================================

* **Runtime coupling.** If the AII, Auth Backend, or OPA is unavailable, the request chain breaks -- there is no fallback path, and the extra hops add latency to every request.
* **Design-time coupling.** Keycloak depends on the AII during login; the Auth Backend depends on the AII and on the client putting the project in the request URL; backend services depend on a header set by the Auth Backend. A change to any one link can silently break the others.
* **Scattered authorization data.** Project-to-data mappings exist in more than one place (:term:`kaapana-backend`, the AII, the DicomWebFilter), so there is more than one place that can disagree about who owns what.
* **No standard pattern for in-cluster, service-to-service calls** -- today's design is built around a browser session, not a service calling another service without a human in the loop.

Future Direction
================

A proposal for hardening authentication (independent of the authorization redesign, which is still open) narrows the platform to four OAuth2 grants, chosen by *how* a client is acting on a user's behalf, rather than leaving every grant type enabled:

.. list-table::
   :header-rows: 1

   * - Scenario
     - Example
     - Grant
   * - Browser login
     - Logging in to the landing page
     - Authorization Code Grant
   * - Client acting for a user, with the user present
     - Dev environments, third-party clients
     - Device Authorization Grant (already used today by :ref:`programmatic API access<concepts_programmatic_access>`)
   * - Backend-to-backend
     - Init-jobs, service DAGs
     - Client Credentials Grant
   * - Client acting for a user, without the user present
     - processing-containers
     - Refresh Token Grant / Client Credentials Grant with OpenID offline access

The Resource Owner Password Credentials Grant and the Implicit Grant are proposed for removal -- both are deprecated in the OAuth 2.1 draft and are a needless risk once the grants above cover every real scenario.
Authorization itself -- untangling the coupling described above -- is explicitly out of scope for this proposal and remains an open design problem.
