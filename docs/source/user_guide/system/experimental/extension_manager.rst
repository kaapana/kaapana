.. _experimental_extension_manager:

Extension Manager
^^^^^^^^^^^^^^^^^

.. warning::

   Experimental and not yet the default. 
   The current supported way of installing extensions is still the ``kube-helm`` based **Extensions** page.

A new service for discovering, installing and managing **Kaapana extensions packaged as OCI artifacts** in any standard container registry. 
An extension bundles reusable *content* (e.g. workflows) that is dispatched to platform services during installation.
Currently, the only supported content type is **workflows** (``workflow-v1``), but the system is designed to be extensible and new content types can be added.
This service will replace the current Helm-chart-based extension collection.

Using it
********

The web UI has three views:

- **Repositories**: add, edit or remove the OCI registries to pull from.
- **Catalog**: browse the extensions available in those registries.
- **Extensions**: install / uninstall extensions and see their state.

Packaging an extension
**********************

Each extension directory contains an ``extension_manifest.json`` describing its contents:

.. code-block:: json

    {
      "name": "my-extension",
      "id": "aaaaaaaa-0000-0000-0000-000000000001",
      "version": "1.0.0",
      "contents": [
        { "name": "my-workflow", "contentType": "workflow-v1",
          "files": [ { "path": "workflow_definition.py" }, { "path": "workflow.json" } ] }
      ]
    }


Build and publish with the ``extensionctl`` CLI (installed from
``lib/kaapana_extensions``):

.. code-block::

    extensionctl login --registry <url> --repo <repo> --user <u> --password <p>
    extensionctl build ./my-extension --push      # tag: <id>-v<version>
    extensionctl pull <tag> ./downloads/

``build`` also accepts a git URL (``git+URL[@ref][#subdir]``); ``push``, ``list``,
``info`` and ``delete`` round out the command set, and the same operations are available as an async Python API.

More details
************

- Service architecture, install/uninstall lifecycle, status state machines, the REST API and more: ``services/base/extension-manager-service/docker/files/app/README.md``
- UI: ``services/base/extension-manager-ui/docker/README.md``.
- ``extensionctl`` cli and python api: ``lib/kaapana_extensions/README.md``.
