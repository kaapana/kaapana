.. _concepts_programmatic_access:

Calling Kaapana Programmatically
##################################

Every workflow-related API in Kaapana -- submit a run, poll its status, query data -- is reachable over plain HTTP, whether the caller is a script on your laptop or a notebook running inside the cluster as a JupyterLab application.
Both authenticate the same way.

Authentication
================

The supported client, ``KaapanaApiService`` from the ``kaapana_client`` package, implements exactly one OAuth2 flow: the **Device Authorization Grant**.
There is no client-credentials grant, so nothing -- not even code running inside the cluster -- can silently mint a token for itself; a human has to approve access once in a browser, after which a long-lived refresh token keeps the client authenticated.

.. note::
   A JupyterLab session launched from the :ref:`Extensions page<extensions>` is handed ``KAAPANA_PROJECT_ID``, ``KAAPANA_CLIENT_ID`` and ``KAAPANA_CLIENT_SECRET`` as environment variables, so ``get_api_service_from_env()`` works out of the box.
   It is **not** handed a pre-authorized token, though: the first API call from a notebook still triggers the same one-time device-approval step as an external script.

.. _client_api_access:

Setting up the client
========================

**Prerequisites**

* The ``kaapana_client`` package is installed (``pip install kaapana_client``).

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
     - UUID of the project you want to operate in.
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
You do **not** need to do this before calling a method -- if the token has not been obtained yet, the first HTTP call will poll for approval automatically (up to 10 attempts, 5 seconds apart) and log the URL again on each retry.

**Token lifecycle**

The service manages tokens transparently:

* **Access token absent** -- triggers the device-code polling loop described above.
* **Access token expired** -- a silent refresh-token grant is performed before the request is sent. No user interaction is required.

Making requests
==================

All five HTTP methods -- ``get``, ``post``, ``put``, ``delete``, and ``head`` -- accept an ``endpoint`` path relative to ``root_url``, followed by any keyword arguments accepted by the underlying ``requests`` library (e.g. ``json``, ``params``, ``data``, ``timeout``).
Authentication headers and the project cookie are injected automatically.

.. code-block:: python

    # GET  /aii/projects
    response = api.get("aii/projects")
    projects = response.json()

    # PUT  /aii/projects/<id>
    response = api.put(f"aii/projects/{project_id}", json={"name": "my-project"})

    # DELETE a resource
    response = api.delete(f"aii/projects/{project_id}")

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

The project the run executes in is taken from the authenticated session, not from the request body.
Poll ``GET workflow-api/v1/workflow-runs/{run_id}`` for its lifecycle status, and ``.../task-runs`` for per-task status and logs.

Future Direction
================

The Workflow API has a ``POST /workflows`` endpoint that registers a workflow definition, but creating a *runnable* workflow today still means building DAG code and a Helm chart and installing them through the Workflow CLI (see :ref:`concepts_workflow_distribution`) -- an external client cannot go from nothing to a runnable workflow through the API alone. Extending programmatic access to cover that full path is a planned future enhancement.
