.. _workflow_extension_with_custom_registry:


Developing a Workflow Extension with a Custom Registry
######################################################

Kaapana workflow extensions can be developed to use processing-container images from a custom container registry instead of the default registry configured for the platform.

This guide demonstrates how to prepare and upload such a workflow extension using a custom registry, based on the **otsus-method-workflow** example.

Prerequisites
=============

The following prerequisites are assumed:

* Access to the Kaapana source code directory.
* Docker installed and configured locally.
* Permissions to create and push images to a custom container registry at :code:`<registry>/<repository>`.
* Access to the Kaapana Web Interface.


Build and Push the Processing-Container Image
=============================================

1. Build the processing-container image for the workflow using the custom registry as the image target::

      docker build -t <registry>/<repository>/otsus-method:<platform-version> .

2. Push the image to the custom registry::

      docker push <registry>/<repository>/otsus-method:<platform-version>

Prepare the Airflow Code and Build the DAG Installer Image
==========================================================

1. Update the Airflow operators to use the custom registry.

   Replace ``{DEFAULT_REGISTRY}`` in the Otsus operators with ``<registry>/<repository>`` so that the operators reference images from the custom registry.

2. Build and push the DAG installer image containing the Airflow code::

      docker build -t <registry>/<repository>/dag-otsus-method:0.0.0 .
      docker push <registry>/<repository>/dag-otsus-method:0.0.0

.. important::

    The image version :code:`0.0.0` is expected here as it matches with the default version in the dag-installer chart.


Deploy the Registry Extension in Kaapana
========================================

Launch the **New Registry** extension in Kaapana and configure it to reference the registry at ``<registry>/<repository>``.


Prepare, Package, and Upload the Workflow Helm Chart
====================================================

#. Update the workflow Helm chart configuration.

   In ``otsus-method/extension/otsus-method-workflow/values.yaml``, set the custom registry URL


    .. code-block:: yaml

        ---
        global:
            image: "dag-otsus-method"
            action: "copy"
            custom_registry_url: "<registry>/<repository>"


#. Package the Helm chart::

      cd otsus-method/extension/otsus-method-workflow
      helm dep up
      helm package .

#. Upload the packaged Helm chart :code:`otsus-method-workflow-0.0.0.tgz` via the **Extensions View** in the Kaapana Web Interface.

.. note::

    The version of the workflow corresponds to the version in the :code:`Chart.yaml` file.