.. _faq_offline_installation:

Offline installation
=====================

Install Kaapana on a server without public-internet access.
There are two installation paths, both driven by the :term:`kaapanactl.sh<kaapanactl>`
script in the ``server-installation`` directory of the repository — pick the one
that matches the target.

- **Single-Registry** — the target can reach an OCI :term:`registry`.
  The installer is pulled from the registry; platform images and charts are pulled
  at deploy time.
- **Air-gap** — the target reaches nothing; everything is moved as tarballs.

Single-Registry
---------------

1. Build host — build and publish
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   kaapana-build \
     --default-registry registry.example.com \
     --username <USER> --registry-password <PASS> \
     --create-offline-installation \
     --publish-offline-installer \
     --skip-platform-images-tarball

This pushes the bootstrap payload as ``<registry>/offline-installer:<version>`` —
the snaps, ``microk8s_base_images.tar`` (MicroK8s system images), the ``gpu-operator``
Helm chart (``gpu-operator.tgz``), ``kaapanactl.sh``, and any
``--offline-extra-file SRC[:DST]`` entries. The **platform Helm chart** and the
platform container images are **not** bundled — the target pulls those from the
registry at deploy. ``--skip-platform-images-tarball`` avoids the multi-GB
platform-images this path doesn't need since we can pull them directly from the
registry at deploy.

2. Target host — pull the installer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bootstrap needs only ``utils/pull_offline_installer.py``. It is self-contained and
uses the Python standard library only — copy that single file to the target and run
it with the system ``python3`` (3.9+); nothing has to be installed first:

.. code-block:: bash

   python3 pull_offline_installer.py \
     --registry-url https://registry.example.com \
     --username <USER> --password <PASS> \
     --tag <version> --target-dir ./microk8s-offline-installer

Use ``http://host:5000`` for a plain-HTTP registry, ``--ca-cert <bundle>`` for a
private CA, or ``--insecure`` to skip verification.

If ``--default-registry`` included a path prefix at build time (e.g.
``registry.example.com/kaapana``), the payload lands under that prefix — pass
``--repository kaapana/offline-installer`` to match.

3. Install and deploy (online deploy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   cd microk8s-offline-installer
   sudo ./kaapanactl.sh install --offline -os Ubuntu

Then perform a regular platform deploy.

Air-gap
-------

1. Build host — build with local tarballs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   kaapana-build \
     --default-registry registry.example.com \
     --username <USER> --registry-password <PASS> \
     --create-offline-installation

Do **not** pass ``--skip-platform-images-tarball`` or ``--publish-offline-installer``
— air-gap needs the local platform-images tarball. This produces, under the build
dir:

- ``microk8s-offline-installer/`` — the bootstrap kit (snaps,
  ``microk8s_base_images.tar``, ``gpu-operator.tgz``, ``kaapanactl.sh``)
- ``<platform>-<version>.tgz`` — the platform Helm chart
- ``<platform>-<version>-images.tar`` — the platform images

2. Target host — copy the artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy all three of the above onto the target by media (USB, scp, …).

3. Install and deploy (offline deploy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   cd microk8s-offline-installer
   sudo ./kaapanactl.sh install --offline -os Ubuntu
   sudo ./kaapanactl.sh deploy --offline \
     --chart-path <platform>-<version>.tgz \
     --import-images-tar <platform>-<version>-images.tar

The chart and platform images come from the copied tarballs; no registry is used.
