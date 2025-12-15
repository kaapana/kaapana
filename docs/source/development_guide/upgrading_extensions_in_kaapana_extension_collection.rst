.. _upgrading_extensions_in_kaapana_extension_collection:


Upgrading an Extension in the Kaapana Extension Collection
##########################################################

The *kaapana-extension-collection* contains all extension Helm charts that are packaged during the Kaapana build process.
These extensions are displayed in the **Extensions View** of the Kaapana Web Interface.

In environments with multiple Kaapana installations, it is often desirable to distribute new or updated extensions centrally.
This can be achieved by adding the extension to the *kaapana-extension-collection*.

This guide demonstrates how to add a new version of an extension to the *kaapana-extension-collection*, using an updated
version of the **JupyterLab** extension as an example.

Prerequisites
=============

The following prerequisites are assumed:

* Access to the Kaapana source directory in which the ``start_build.sh`` script was executed.
* Access to the ``build/`` directory within the Kaapana source directory.

Update the Helm Chart
=====================

1. Navigate to the JupyterLab Helm chart directory::

      cd services/applications/jupyterlab/jupyterlab-chart

2. Update the chart version:

   * In ``Chart.yaml``, update line 5 to::

         version: "2.0.0"

3. Update the chart dependencies:

   * In ``requirements.yaml``, add the following repository entry (around line 5)::

         repository: file://../../../utils/kaapana-library-chart/

Package the Helm Chart and Add It to the Extension Collection
=============================================================

1. Update dependencies and package the Helm chart::

      helm dep up
      helm package .

2. Copy the packaged chart to the *kaapana-extension-collection* charts directory::

      cp jupyterlab-chart-2.0.0.tgz \
         ../../../../build/kaapana-admin-chart/kaapana-extension-collection/charts/

Build and Push the Updated Extension Collection Image
=====================================================

1. Navigate to the extension collection build directory::

      cd ../../../../build/kaapana-admin-chart/kaapana-extension-collection/

2. Build and push the Docker image::

      docker build -t <registry-domain>/<repository>/kaapana-extension-chart:<platform-version> .
      docker push <registry-domain>/<repository>/kaapana-extension-chart:<platform-version>

Update the Extension Collection in Kaapana
==========================================

1. Open the Kaapana Web Interface.
2. Navigate to the **Extensions View**.
3. Click the cloud icon to download the updated extension collection.
4. Verify that two versions of the JupyterLab extension are available, including version **2.0.0**.
