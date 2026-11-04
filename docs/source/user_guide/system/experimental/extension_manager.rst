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
- **Extensions**: install / uninstall extensions and see their state, or install an extension from a file.

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

Installing without internet
***************************

On a platform without access to a registry, install an extension from an archive built with ``extensionctl``.

1. On a machine with the extension sources, build the archive:

   .. code-block::

       extensionctl build ./my-extension --output ./dist/   # ./dist/my-extension-v1.0.0.tar.gz

2. Copy the ``.tar.gz`` file to a computer that can open the platform.
3. Open the Extension Manager, go to **Extensions** and select **Install from file**.
4. Choose the archive and select **Install**. The archive is checked before the installation starts, and the extension then appears in the list with the source *Uploaded file*.

The extension is installed in the same way as one from a repository.
Its details show the file name and the user who uploaded it.
If an archive is rejected, the message names the problem. If an installation fails, its details show the reason.
To install it again after a failed installation, upload the same archive again.

Limitations:

- Archives can be up to 100 MB, and up to 500 MB once unpacked.
- Archives may only contain the manifest and the files it lists. Links are not allowed.
- Archives must not contain container images yet. The workflows can only use images that are already available on the platform.
- An extension with the same ``id`` can only be installed once, whether from a file or from a repository. Uninstall the installed version before you install another one.

More details
************

- Service architecture, install/uninstall lifecycle, status state machines, the REST API and more: ``services/base/extension-manager-service/docker/files/app/README.md``
- UI: ``services/base/extension-manager-ui/README.md``.
- ``extensionctl`` cli and python api: ``lib/kaapana_extensions/README.md``.
