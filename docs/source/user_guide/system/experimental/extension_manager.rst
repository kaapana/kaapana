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

- **Repositories**: add, edit or remove the OCI registries to pull from. The built-in **Upload** repository holds the uploaded extensions and cannot be changed or removed.
- **Catalog**: browse the extensions available in those registries and install them. **Upload extension** adds a ``.tar.gz`` built with ``extensionctl build`` to the Upload repository.
- **Extensions**: see the state of installed extensions and uninstall them.

Each platform comes with the repository ``kaapana-default``. It points to
``https://<registry>/extensions``, where ``<registry>`` is the registry the
platform was deployed from. It is meant for the extensions that are published
with the platform. The Extension Manager registers it on every start and
resets its URL and credentials. It is not registered in offline mode. See
:ref:`extension_manager` for the rules that apply to this repository.

Installing a newer version of an installed extension from the same repository updates it in place. Its workflows keep their IDs, revisions and runs. Older versions cannot be installed over a newer one. For an uploaded extension, upload the newer version and install it from the Upload repository.

Installing without internet
***************************

A platform without internet access cannot reach a registry. Its extensions are uploaded instead:

1. On a machine with internet access, build the archive with ``extensionctl build ./my-extension``.
2. Copy the ``.tar.gz`` to a machine that can open the platform.
3. In the **Catalog**, click **Upload extension** and choose the archive.
4. Open the uploaded extension in the **Catalog** and click **Install**.

Uploaded extensions are stored in a local OCI registry that ships with the platform. They stay there until they are removed with **Remove upload** in their catalog entry. Removing an upload does not uninstall the extension. Archives can be at most 100 MB. Archives that contain container images are not supported yet.

Installing does not pull container images. A workflow pulls its images from their registries the first time it is started, and without internet that pull fails. The extension still installs, but its workflows only run if their container images are already on the platform.

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
- UI: ``services/base/extension-manager-ui/README.md``.
- ``extensionctl`` cli and python api: ``lib/kaapana_extensions/README.md``.
