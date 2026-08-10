.. _concepts_programmatic_access:

Calling Kaapana Programmatically
##################################

Every workflow-related API in Kaapana -- submit a run, poll its status, query data -- is reachable over plain HTTP, whether the caller is a script on your laptop or a notebook running inside the cluster as a JupyterLab application.
Both authenticate the same way.

Authentication
================

The supported client, ``KaapanaApiService`` from the ``kaapana_client`` package, implements exactly one OAuth2 flow: the **Device Authorization Grant**.
There is no client-credentials grant, so nothing -- not even code running inside the cluster -- can silently mint a token for itself; a human has to approve access once in a browser, after which a refresh token keeps the client authenticated.

.. note::
   The ``offline_access`` scope is **deprecated** and will be removed in the next release. It is being phased out step by step -- the initial device-authorization request no longer includes it, though it is still requested during token exchange for this release.

.. note::
   A JupyterLab session launched from the :ref:`Extensions page<extensions>` is handed ``KAAPANA_PROJECT_ID``, ``KAAPANA_CLIENT_ID`` and ``KAAPANA_CLIENT_SECRET`` as environment variables, so ``get_api_service_from_env()`` works out of the box.
   It is **not** handed a pre-authorized token, though: the first API call from a notebook still triggers the same one-time device-approval step as an external script.

.. _client_api_access:

Setting up the client
========================

**Prerequisites**

* The ``kaapana_client`` package is installed from the Kaapana repository (``pip install ./kaapana/lib/kaapana_client``).

**Initialization**

``KaapanaApiService`` requires four constructor arguments:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``root_url``
     - Base URL of the Kaapana instance (e.g. the Traefik gateway URL). All endpoint paths are appended to this value.
   * - ``project_id``
     - The project you want to operate in: its UUID, its 8-character ``short_id`` or its name. It becomes the ``/project/<id>/`` URL prefix on calls to project-scoped services (see below).
   * - ``client_id``
     - OAuth2 client ID registered in Keycloak.
   * - ``client_secret``
     - OAuth2 client secret for the given client, or ``None`` for public clients.

When you create a ``KaapanaApiService`` instance, it immediately requests a device code from Keycloak and prints a verification URL to the log:

.. code-block:: python

    from kaapana_client.services.ApiService import KaapanaApiService

    api = KaapanaApiService(
        root_url="https://<host>",
        project_id="d7e991b3-9463-48e7-98c2-661da8b83018",
        client_id="kaapana",
        client_secret=None,
    )
    # INFO - Open the following URL in a browser to grant the ApiService
    #        access to Kaapana: https://<host>/auth/realms/kaapana/device?user_code=XXXX-YYYY

As a convenience, if the required values are available as environment variables, you can use the ``get_api_service_from_env`` factory function instead:

.. code-block:: python

    from kaapana_client.services.ApiService import get_api_service_from_env

    api = get_api_service_from_env()

Open the printed URL in a browser and confirm access with a Kaapana account.
You do **not** need to do this before calling a method -- if the token has not been obtained yet, the first HTTP call will poll for approval automatically, with no limit on how long it waits. If the device code expires before you approve it, the client silently starts a new device authorization grant and prints a fresh URL, rather than giving up.

**Token lifecycle**

The service manages tokens transparently:

* **Access token absent** -- triggers the device-code polling loop described above.
* **Access token expired** -- a silent refresh-token grant is performed before the request is sent. No user interaction is required.

Making requests
==================

All five HTTP methods -- ``get``, ``post``, ``put``, ``delete``, and ``head`` -- accept an ``endpoint`` path relative to ``root_url``, followed by any keyword arguments accepted by the underlying ``requests`` library (e.g. ``json``, ``params``, ``data``, ``timeout``).
Authentication headers are injected automatically, and so is the project scope.

.. code-block:: python

    # GET  /aii/projects
    response = api.get("aii/projects")
    projects = response.json()

    # PUT  /aii/projects/<id>
    response = api.put(f"aii/projects/{project_id}", json={"name": "my-project"})

    # DELETE a resource
    response = api.delete(f"aii/projects/{project_id}")

**Project scope**

Kaapana carries the project in the URL -- see :ref:`project_scoping` for the mechanism -- and the client applies that convention for you.
A call to one of the project-scoped services (``kaapana-backend``, ``kube-helm-api``, ``workflow-api``, ``dicom-web-filter``) is sent to ``/project/<project_id>/<endpoint>``; every other endpoint is sent unprefixed, because no project-scoped route exists for it.

.. code-block:: python

    # sent as GET /project/<project_id>/kaapana-backend/client/datasets
    response = api.get("kaapana-backend/client/datasets")

    # sent as GET /aii/projects -- not a project-scoped service
    response = api.get("aii/projects")

The gateway resolves the id, verifies that the authenticated user is a member of that project, and injects the resolved project as a trusted ``Project`` header before the service sees the request.
Two consequences worth knowing:

* Scoping to a project you are not a member of is a hard **403** -- there is no fallback to a default project. Realm admins may scope anywhere.
* To address a *different* project in a single call, write the prefix yourself. An ``endpoint`` that already starts with ``project/`` is passed through untouched:

  .. code-block:: python

     api.get(f"project/{other_project_id}/kaapana-backend/client/datasets")

.. note::
   Earlier releases carried the scope in a ``Project`` cookie. That cookie is gone -- nothing writes or reads it. A request without the URL prefix simply carries no project context, so endpoints that require one answer **400**.

Triggering a workflow run
============================

Submitting a run is a single call to the Workflow API:

.. code-block:: python

   from kaapana_client.services.ApiService import get_api_service_from_env

   api = get_api_service_from_env()

   response = api.post(
       "workflow-api/v1/workflow-runs",
       json={
           "workflow": {"id": "<workflow-uuid>", "increment": 1},
           "workflow_parameters": [],
           "cleanup_policy": "on_success",  # "never" | "on_success" | "always"
       },
   )
   run_id = response.json()["id"]

The project the run executes in comes from the URL prefix the client adds, not from the request body -- the endpoint rejects a request without it with **400**.
Poll ``GET workflow-api/v1/workflow-runs/{run_id}`` for its lifecycle status, and ``.../task-runs`` for per-task status and logs.
