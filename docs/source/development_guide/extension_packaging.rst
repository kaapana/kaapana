.. _extension_packaging:

=====================================
Packaging and Publishing Extensions
=====================================

Kaapana extensions are OCI artifacts that bundle one or more workflow definitions
into a distributable package. Once published to an OCI-compatible registry, they
can be discovered and installed by other Kaapana deployments through the Extension
Manager.

This guide walks through creating, building, and publishing a workflow extension
using the ``extensionctl`` command-line tool provided by the ``kaapana_extensions``
library.

.. note::

   This guide assumes you have already developed a processing container (see
   :doc:`processing_container_dev_guide`) and an Airflow DAG for your workflow
   (see :doc:`workflow_development`). The container image and the DAG file are
   the inputs to the packaging process described here.


What is a Kaapana Extension?
-----------------------------

A Kaapana extension is a versioned OCI artifact stored in a standard container
registry. It contains:

- An **extension manifest** (``extension_manifest.json``) that declares the
  extension's identity, version, and contents.
- One or more **content items**, each of a specific content type. For
  workflow extensions the content type is ``workflow-v1``.

A ``workflow-v1`` content item consists of an Airflow DAG definition file and
optionally a ``workflow.json`` metadata file that describes how the workflow
appears in the Kaapana UI.

The processing container image is **not** bundled into the extension. It is
referenced by name inside the DAG file and pulled from the registry at the time
the workflow runs.


Extension Directory Structure
------------------------------

An extension is built from a local directory. The directory must contain
``extension_manifest.json`` at its root. Each content item lives in its own
subdirectory named after the content item:

.. code-block:: text

   my-workflow-extension/
   ├── extension_manifest.json
   └── my-workflow/
       ├── workflow_definition.py
       └── workflow.json


The Extension Manifest
-----------------------

``extension_manifest.json`` declares the extension's identity and contents.
Example for a single-workflow extension:

.. code-block:: json

   {
     "name": "my-workflow-extension",
     "id": "aaaaaaaa-0000-0000-0000-000000000001",
     "version": "1.0.0",
     "contents": [
       {
         "name": "my-workflow",
         "contentType": "workflow-v1",
         "files": [
           { "path": "workflow_definition.py" },
           { "path": "workflow.json" }
         ]
       }
     ]
   }

``name``
  Alphanumeric identifier for the extension (hyphens and underscores allowed).
  Used as the human-readable label in the Extension Manager.

``id``
  A stable UUID that uniquely identifies this extension across all registries.
  Omit this field on the first build — ``extensionctl`` generates it
  automatically and writes it back into the manifest. Once set, do not change
  the ``id``: it is used to derive registry tags and must stay stable across
  versions.

``version``
  Semantic version (``MAJOR.MINOR.PATCH``). Increment this before each
  publish. The ``extensionctl`` tool can bump the version automatically
  (see :ref:`publishing_ext`).

``contents``
  List of content items bundled in this extension. Each item specifies:

  - ``name`` — identifier for this content item; must match the subdirectory name
  - ``contentType`` — ``workflow-v1`` for Airflow DAG workflows
  - ``files`` — file paths relative to the content item's subdirectory


Installing extensionctl
------------------------

The ``extensionctl`` CLI is part of the ``kaapana_extensions`` library.
It depends on ``kaapana_containers``.
Install it via pip from the Kaapana repository:

.. code-block:: bash
  
   pip install ./kaapana/lib/kaapana_containers
   pip install ./kaapana/lib/kaapana_extensions

Verify the installation:

.. code-block:: bash

   extensionctl --help


Building the Extension
-----------------------

Run ``extensionctl build`` pointing at your extension directory. The command
validates the manifest and produces a ``.tar.gz`` archive:

.. code-block:: bash

   extensionctl build ./my-workflow-extension/ --output ./dist/

The archive is named from the extension ``name`` and version, for example
``my-workflow-extension-v1.0.0.tar.gz``.

To build all extensions found recursively under a directory:

.. code-block:: bash

   extensionctl build ./extensions/ --recursive --output ./dist/


.. _publishing_ext:

Publishing the Extension
-------------------------

Authenticating with a Registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Authenticate with the target OCI registry before pushing:

.. code-block:: bash

   extensionctl login \
     --registry https://registry.example.com \
     --repo kaapana/extensions \
     --user myuser \
     --password mytoken

Credentials are saved to ``~/.kaapana/credentials.json`` and reused for
subsequent commands targeting the same registry.

Pushing the Extension
~~~~~~~~~~~~~~~~~~~~~~

Push a built archive to the configured registry:

.. code-block:: bash

   extensionctl push ./dist/my-workflow-extension-v1.0.0.tar.gz

To build and push in a single step with an automatic version bump:

.. code-block:: bash

   extensionctl build ./my-workflow-extension/ --push --bump patch

The ``--bump`` flag accepts ``major``, ``minor``, or ``patch`` and increments
the latest version in the repository before pushing.

Verifying the Published Extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List extensions in the registry to confirm the push succeeded:

.. code-block:: bash

   extensionctl list --full

This prints each extension's name, version, and content types. The published
extension can now be added to any Kaapana deployment via the Extension Manager
(see :doc:`extension_manager`).
