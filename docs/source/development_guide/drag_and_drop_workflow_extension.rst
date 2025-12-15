.. _drag_and_drop_workflow_extension:


Uploading a Workflow Extension via the Extensions View
######################################################

Workflow extensions can be uploaded to Kaapana using the drag-and-drop functionality in the **Extensions View**.

To make a new workflow extension fully available on the platform, the following artifacts must be uploaded:

* All processing-container images used by the workflow.
* A Docker image containing the Airflow code (DAG files and custom operator implementations).
* The packaged Helm chart for the workflow extension.

This guide demonstrates how to prepare a workflow extension and how to upload it to the platform, using the **otsus-method-workflow** extension as an example.

Prerequisites
=============

The following prerequisites are assumed:

* Access to the kaapana code directory
* Access to the private registry that is used by your Kaapana Installation.

Build Processing Containers
===========================

1. From the root level of the kaapana code directory navigate to the directory of the only custom processing-container image used in the otsus-method workflow::
    
    cd templates_and_examples/examples/processing-pipelines/otsus-method/processing-containers/otsus-method

2. Build the processing-container with the expected image tag::
    
    docker build -t <registry>/<repository>/otsus-method:<plaform-version> .


Prepare the Airflow Code and Build the DAG Installer Image
==========================================================

1. Adapt image_pull_policy of Airflow operators

    Add the line :code:`image_pull_policy="IfNotPresent",` to both operators in :code:`templates_and_examples/examples/processing-pipelines/otsus-method/extension/docker/files/otsus-method/`.

    .. code-block:: python

        class OtsusMethodOperator(KaapanaBaseOperator):
            def __init__(
                self,
                dag,
                name="otsus-method",
                execution_timeout=timedelta(seconds=120),
                *args,
                **kwargs,
            ):
                super().__init__(
                    dag=dag,
                    name=name,
                    image=f"{DEFAULT_REGISTRY}/otsus-method:{KAAPANA_BUILD_VERSION}",
                    image_pull_secrets=["registry-secret"],
                    image_pull_policy="IfNotPresent",
                    execution_timeout=execution_timeout,
                    *args,
                    **kwargs,
                )

    and

    .. code-block:: python

        class OtsusNotebookOperator(KaapanaBaseOperator):
            def __init__(
                self,
                dag,
                name="otsus-notebook-operator",
                execution_timeout=timedelta(minutes=20),
                *args,
                **kwargs,
            ):
                super().__init__(
                    dag=dag,
                    name=name,
                    image=f"{DEFAULT_REGISTRY}/otsus-method:{KAAPANA_BUILD_VERSION}",
                    image_pull_secrets=["registry-secret"],
                    image_pull_policy="IfNotPresent",
                    execution_timeout=execution_timeout,
                    ram_mem_mb=1000,
                    ram_mem_mb_lmt=3000,
                    *args,
                    **kwargs,
                )


2. Build the DAG installer image containing the Airflow code with the correct image tag::

    cd ../../extension/docker/
    docker build -t <registry>/<repository>/dag-otsus-method:0.0.0 .

.. important::

    The image version :code:`0.0.0` is expected here as it matches with the default version in the dag-installer chart.


Save and Upload Docker Images
=============================

1. Save all required Docker images into a single archive::

      docker save <registry>/<repository>/otsus-method:<plaform-version> <registry>/<repository>/dag-otsus-method:0.0.0 -o images.tar

2. Upload the ``images.tar`` file via the **Extensions View** in the Kaapana Web Interface.

Prepare, Package, and Upload the Helm Chart
===========================================

#. Navigate to the helm chart directory::

    cd ../otsus-method-workflow/

#. Update ``values.yaml`` with the following settings:

    .. code-block:: yaml

        ---
        global:
            image: "dag-otsus-method"
            action: "copy"
            pull_policy_images: IfNotPresent

#. Update chart dependencies and package the Helm chart::

      helm dep up
      helm package .

#. Upload the packaged Helm chart :code:`otsus-method-workflow-0.0.0.tgz` via the **Extensions View**.

.. note::

    The version of the workflow corresponds to the version in the :code:`Chart.yaml` file.
