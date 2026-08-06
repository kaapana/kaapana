.. _project_scoping:

=================================
URL-based Project Scoping
=================================

Kaapana separates data per :term:`project`. Every request that touches
project-scoped data must therefore carry *which* project it targets. This page
describes the platform-wide convention for that: **the project is part of the
URL**.

.. code-block:: text

   /project/<id>/<service-path>

   /project/3f9ac81b/kaapana-backend/client/datasets
   /project/3f9ac81b/kube-helm-api/extensions

``<id>`` may be the project's 8-character ``short_id`` (preferred), its UUID, or
its name — AII's ``GET /projects/{identifier}`` resolves all three.

Because the scope is in the URL, it works for *every* kind of request — XHR,
iframe document loads, DICOMweb media fetches, downloads, ``curl`` — and a URL
copied out of the browser keeps its project context. Two tabs can work on two
different projects at the same time, and access logs show the scope of every
request.


How a request is authorized and scoped
======================================

Every request entering the platform passes traefik's global ``auth-check``
forward-auth middleware, which calls **auth-backend**:

1. auth-backend matches the requested path against ``^/project/([^/]+)(/.*)?``.
   Only ``x-forwarded-uri`` is read — it is the URI traefik's forwardAuth sets
   itself. ``auth-check`` is an *entrypoint* middleware, so no router middleware
   has run yet and nothing sets ``x-forwarded-prefix``; a client-supplied value
   must never influence authorization.
2. On a match it resolves the id via AII, and validates that the response really
   is a project object. An unresolvable id leaves the path **unstripped** and
   attaches no project, so the service receives no ``Project`` header and its
   ``get_project`` dependency answers **400**. That missing header is what makes
   it safe — *not* a policy miss: role ``admin``'s catch-all ``^/.*`` matches an
   unstripped ``/project/<bogus>/…`` path.

   Enrichment from the URL prefix additionally requires an access token.
   Unauthenticated requests reach the gateway only on oauth2-proxy's
   ``skip_auth_routes`` (``^/auth/.*``, ``^/kaapana-backend/remote/.*``,
   ``^/oauth2/metrics$``), none of which read the ``Project`` header. The legacy
   cookie branch (see the note below) is *not* token-gated, so on one of those
   routes an anonymous request carrying a ``Project`` cookie does reach AII.
3. **Membership is enforced here.** Resolving a project proves it exists, not
   that the caller may use it. A non-admin may scope only to projects listed in
   their access token's ``projects`` claim; admins may scope anywhere. A missing,
   null or malformed claim yields an empty member set, so the check **fails
   closed**. The bare ``/project/<id>`` document is the only exemption — it
   carries no project data of its own.
4. The resolved project becomes ``input.project`` for the OPA policy
   evaluation, and the ``/project/<id>`` prefix is **stripped** from
   ``input.requested_prefix`` — so all policies keep matching the plain
   service paths (``^/kaapana-backend/.*`` etc.).
5. If OPA allows the request, auth-backend returns the full project object
   (``id``, ``name``, ``short_id``, ``opensearch_index``, ``s3_bucket``, …) in
   a ``Project`` response header. Traefik copies it onto the forwarded request
   (``authResponseHeaders``) — after removing any ``Project`` header the
   client may have sent, so the header **cannot be spoofed**.
6. The per-service traefik middlewares (``strip-project-prefix`` + the
   service's own strip-prefix) remove both URL prefixes, so the service
   receives the plain path plus the trusted, enriched ``Project`` header.

Services never parse URLs or query AII themselves — they read the ``Project``
request header (see ``kaapana-backend``'s ``get_project`` dependency for the
canonical example).

.. warning::

   A shared deep link into a project the user is not a member of returns a hard
   **403**. There is no soft fallback to the user's own project: the scope named
   in the URL is the scope that is authorized, or the request is refused.

   The bare ``/project/<id>`` shell document is the one exemption, and it is a
   deliberate trade-off: it normalizes to ``/``, which the policy allows for
   every role, so any authenticated user gets **200** for a project they are not
   a member of — a project-existence oracle over UUIDs, short ids and project
   names. Accepted, because that route serves nothing but the shell document:
   every ``/project/<id>/<service>`` route requires a service segment, so the
   bare shapes reach only the root ingress, which has no ``Project``-header
   consumer, and the enriched header is a forwardAuth *response* header that
   never travels back to the client.

.. note::

   **Legacy ``Project`` cookie.** Requests *without* a ``/project/<id>`` prefix
   still take their scope from the ``Project`` browser cookie, which the current
   landing page writes: auth-backend resolves it via AII and injects the same
   enriched header. That path is deliberately **not** membership-gated — the
   gate fails closed on a missing ``projects`` claim, which would deny traffic
   that works today — so it remains possible to scope to a foreign project by
   setting the cookie. Both the derivation and that residual gap go away when
   the UI moves to the URL prefix. ``workflow-api`` and ``dicom-web-filter``
   additionally read the cookie *themselves* rather than the header; until they
   switch, their project-scoped routes carry the scope in the URL but do not yet
   act on it.


Making a service project-scoped
===============================

A service becomes reachable under ``/project/<id>/<service>/...`` with one
traefik ``IngressRoute`` next to its regular ``Ingress``:

.. code-block:: yaml

   apiVersion: traefik.io/v1alpha1
   kind: IngressRoute
   metadata:
     name: my-service-project-ingressroute
     namespace: "{{ .Values.global.services_namespace }}"
   spec:
     entryPoints:
       - websecure
     routes:
       - kind: Rule
         match: PathRegexp(`^/project/[^/]+/my-service(/|$)`)
         middlewares:
           - name: strip-project-prefix
           - name: strip-prefix-my-service
         services:
           - name: my-service
             port: 8080

``strip-project-prefix`` exists once per namespace, since cross-namespace
middleware references are disabled: the services-namespace copy comes from the
platform chart, the admin-namespace copy from the traefik chart. Reference the
copy in the namespace the ``IngressRoute`` itself lives in. The regular
unprefixed route stays — requests through it simply carry no project context.

In the service, read the project from the enriched header:

.. code-block:: python

   def get_project(request: Request) -> dict:
       project_header = request.headers.get("Project")
       if not project_header:
           raise HTTPException(status_code=400, detail="Missing Project header")
       return json.loads(project_header)

Currently scoped services: ``kaapana-backend``, ``kube-helm-api``,
``workflow-api``, ``dicom-web-filter``.

OHIF and Slim are ``path``-scoped viewers: their document URL decides the scope.
Served under ``/project/<id>/ohif/`` or ``/project/<id>/slim/`` their runtime
configs derive router basename and DICOMweb roots from ``window.location``;
opened without the prefix they use the plain, unscoped dicom-web-filter route,
exactly as before.

.. note::

   Link the **trailing slash**. Slim's nginx conf serves the app from
   ``location /slim/`` only; a slashless ``/project/<id>/slim`` is stripped to
   ``/slim``, falls through to the catch-all ``location /`` and is redirected to
   the absolute ``/slim/`` — losing the project prefix. Slim has no
   trailing-slash middleware at all. OHIF has one,
   ``ohif-project-trailing-slash``, but its ``redirectRegex`` is
   ``^.*/project/([^/]+)/ohif$`` — ``$``-anchored, so it repairs
   ``/project/<id>/ohif`` and *not* ``/project/<id>/ohif?mode=x``, which degrades
   exactly like Slim's slashless shape.
