.. _workflow_extension_with_custom_registry:


Developing a Workflow Extension with a Custom Registry
######################################################

Kaapana workflow extensions can be developed to use processing-container images from a custom container registry instead of the default registry configured for the platform.

This guide demonstrates how to prepare and upload such a workflow extension using a custom registry, based on the **otsus-method-workflow** example.
The guide consists of two steps

#. Providing the processing-container images for the operators
#. Preparing the extension-chart with the Airflow code such as the dag file and operator files

Prerequisites
=============

The following prerequisites are assumed:

* Access to the Kaapana source code directory
* Docker installed and configured locally
* Helm installed
* Permissions to create and push images to a custom container registry at :code:`<protocol>://<registry>:<port>/<repository>`
* Access to the Kaapana Web Interface

Provide processing-container images
====================================


Build and Push the Processing-Container Image
-----------------------------------------------

Build and push the processing-container images for your operators to the custom registry::

      docker build -t <registry>:<port>/<repository>/otsus-method:1.0.0 .
      docker push <registry>:<port>/<repository>/otsus-method:1.0.0


Launch a New Registry extension with scope *Project-Secret*
------------------------------------------------------------------

For each project that should be able to use these processing-container images launch a **New Registry** extension in Kaapana.
Configure it as follows:

* **display_name:** Choose a unique and identifiable name for this *New Registry*, e.g. REGISTRY-<project-name>-<registry-name>
* **secret_scope:** Project-Secret
* **custom_registry_url:** *<protocol>://<registry>:<port>/<repository>*
* **credentials_curstom_registry_username:** The username to access the registry
* **credentials_curstom_registry_password:** The password to access the registry
* **test_pull_image:** <registry>:<port>/<repository>/otsus-method:1.0.0

This will create the registry-secret in the selected active project.

.. important::
      
      The *Absolute Registry URL* for the New Registry has to contain the protocol, either *http* or *https*.
      For more information about installation errors and configuration options checkout the :ref:`documentation <extensions_new_registry>`.

Prepraing the extension-chart
===============================

Prepare the Airflow Code and Build the DAG Installer Image
-----------------------------------------------------------

1. Set the :code:`image` parameter of your operators according to the processing-container images you pushed to your registry without the protocol.

   Set :code:`image="<registry>:<port>/<repository>/otsus-method:1.0.0",` in :code:`OtsusNotebookOperator.py` and :code:`OtsusMethodOperator.py`.

2. Build and push the DAG installer image containing the Airflow code::

      docker build -t <registry>:<port>/<repository>/dag-otsus-method:0.0.0 .
      docker push <registry>:<port>/<repository>/dag-otsus-method:0.0.0

.. important::

    The image version :code:`0.0.0` of the dag-otsus-method image is necessary as it matches with the default version in the dag-installer chart.

Prepare, Package, and Upload the Workflow Helm Chart
------------------------------------------------------

#. Update the workflow Helm chart configuration.

Set the custom registry URL in ``otsus-method/extension/otsus-method-workflow/values.yaml``.


    .. code-block:: yaml

        ---
        global:
            image: "dag-otsus-method"
            action: "copy"
            custom_registry_url: "<protocol>://<registry>:<port>/<repository>"

#. Specify the version of the chart in :code:`Chart.yaml`

      .. code-block:: yaml

            ---
            ...
            name: otsus-method-workflow
            version: "1.0.0"
            ...
        
#. Specify the relative path to the dag-installer-chart in :code:`requirements.yaml`

      .. code-block:: yaml

            ---
            dependencies:
            - name: dag-installer-chart
            version: 0.0.0
            repository: file://<relative-path-to-dag-installer-chart>

      You find the dag-installer chart at :code:`/services/utils/dag-installer-chart` in the kaapana repository.
            
#. Package the Helm chart::

      cd otsus-method/extension/otsus-method-workflow
      helm dep up
      helm package .

#. Upload the packaged Helm chart :code:`otsus-method-workflow-1.0.0.tgz` via the **Extensions View** in the Kaapana Web Interface.

.. note::

    The version of the workflow corresponds to the version in the :code:`Chart.yaml` file.


Launch a New Registry Extension with scope *Service-Secret*
-------------------------------------------------------------

Launch a **New Registry** extension in Kaapana.
Configure it as follows:

* **display_name:** Choose a unique and identifiable name for this *New Registry*, e.g. REGISTRY-service-<registry-name>
* **secret_scope:** Service-Secret
* **custom_registry_url:** *<protocol>://<registry>:<port>/<repository>*
* **credentials_curstom_registry_username:** The username to access the registry
* **credentials_curstom_registry_password:** The password to access the registry
* **test_pull_image:** <registry>:<port>/<repository>/dag-otsus-method:0.0.0

This will create a registry-secret that will be used to pull the image with the Airflow code.

.. important::
      
      The registry-url for the New Registry has to contain the protocol either *http* or *https*.
      For more information about installation errors and configuration options checkout the :ref:`documentation <extensions_new_registry>`.
