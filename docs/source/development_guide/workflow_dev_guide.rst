.. _workflow_dev_guide:

==============================
Developing Workflow Extensions
==============================

Introduction
************
Kaapana is built on technologies that allow many ways of developing workflows for the platform.
Since mentioning all of these steps can make the guide difficult to follow, it is instead structured with a goal to provide the most straightforward and easy to follow approach to ensure development reproducability in as many use cases as possible.
That being said, we always appreciate if you reach out to us on Slack if you have any suggestions for improving this document.

When possible, there will still be multiple options in separate tabs for completing some steps below.
However, if you are not sure about an advanced option, proceed with the one in the leftmost tab as this should work in most scenarios.

.. important:: 
    | This guide assumes that:
    |
    | 1. You already have a running Kaapana platform with admin access
    | 2. You have a basic understanding of the Kaapana platform and its components, if not please refer to the :ref:`user_guide`
    | 3. You have access to a terminal where the platform is running (if you are using EDK, you can skip this step)
    | 4. You have a local development environment with access to internet, you have either Docker or Podman installed, and you have the `Kaapana repository <https://codebase.helmholtz.cloud/kaapana/kaapana/-/tree/master>`_ cloned (if you are using EDK, you can skip this step)

    If you do not have an access to a terminal where Kaapana is deployed, you can still use EDK (Extension Development Kit) :ref:`_extensions_edk` inside the platform directly.
    For that, the Kaapana version should be at least :code:`0.4.0` , and there needs to be internet access on the machine where it is deployed.
    You can reach out to us on Slack if you do not satisfy these conditions.


Throughout this guide, a simple workflow extension called ``otsus-method`` will be used as example. You can find the code in the `templates_and_examples folder in the Kaapana repository <https://codebase.helmholtz.cloud/kaapana/kaapana/-/tree/develop/templates_and_examples/examples/processing-pipelines/otsus-method>`_ .

Kaapana has a convention for the folder structure of extensions, which is recognized by other internal tools such as the build script. Therefore it is important to know what each directory contains.
The folder structure of the example ``otsus-method`` extension is as follows:

.. code-block:: otsus_method

    otsus-method
    ├── extension
    │   ├── docker
    │   │   ├── Dockerfile
    │   │   └── files
    │   │       ├── dag_otsus_method.py
    │   │       └── otsus-method
    │   │           ├── OtsusMethodOperator.py
    │   │           └── OtsusNotebookOperator.py
    │   └── otsus-method-workflow 
    │       ├── Chart.yaml
    │       ├── README.md
    │       ├── requirements.yaml
    │       └── values.yaml
    └── processing-containers
        └── otsus-method
            ├── Dockerfile
            └── files
                ├── otsus_method.py
                ├── otsus_notebooks
                │   ├── run_otsus_report_notebook.ipynb
                │   └── run_otsus_report_notebook.sh
                └── requirements.txt

On a high level, it is conceptually divided into two main parts: ``extension`` (i.e. configuration files) and ``processing-containers`` (i.e. actual code).
The details will be explained in the following sections below.


Step 1: Helm Chart Configuration
********************************

``extension/otsus-method-workflow`` directory contains everything regarding the configuration of the Helm chart, which is used to deploy the workflow.
This usually only includes files expected by Helm, such as ``Chart.yaml``, ``values.yaml``, ``requirements.yaml``, ``README.md`` and sometimes a ``templates`` directory. More details about these files can be found in the `Helm documentation <https://helm.sh/docs/topics/charts/>`_.

For a custom workflow extension, the following should be ensured inside the ``extension/otsus-method-workflow`` directory:

.. tabs::

      .. tab:: Local Dev
        
        1. ``Chart.yaml`` is filled with the correct information about your extension 
        2. ``requirements.yaml`` file contains  all the dependencies of your extension, and a correct path to :code:`dag-installer-chart` dir inside the cloned Kaapana repository
        3. ``values.yaml`` file only contains

        .. code-block:: yaml

            ---
            global:
                image: "<dag-image-name>" # NOTE: will be explained in Step 2
                action: "copy"
        

      .. tab:: EDK

        1. ``Chart.yaml`` is filled with the correct information about your extension
        2. ``requirements.yaml`` file contains  all the dependencies of your extension, and :code:`dag-installer-chart` with path :code:`file:///kaapana/app/kaapana/services/utils/dag-installer-chart/`
        3. ``values.yaml`` contains:
        
        .. code-block:: yaml
            ---
            global:
                image: "<dag-image-name>" # NOTE: will be explained in Step 2
                action: "copy"
                pull_policy_images: "IfNotPresent"
                custom_registry_url: "localhost:32000"


Step 2: Airflow Configuration
*************************************************

``extension/docker`` is where the information that is passed to the Airflow is stored. 

TODO: dags and operators, operators should have "operator" in their filename, DEFAULT_REGISTRY and other variables

Step 3: Code for Data Processing
*************************************************

TODO: can be whatever you want, only for the Dockerfile it is important that it is built on top of the base python image

``processing-containers`` directory is where the actual code that runs inside the containers pulled by the Airflow operators is stored.
It is possible to have multiple processing containers for multiple operators inside the same extension, but they should be in separate folders.


Step 4: Building All Containers of the Extension
*************************************************

TODO: docker or podman build
TODO: finding out the registry url, version etc


Step 5: Putting Containers in a Running Platform
************************************************

TODO: upload via UI, takes too long
TODO: explain the debugging options if the containers are not uploaded correctly


Step 6: Packaging the Helm Chart
*************************************************

TODO: 


Step 7: Putting the Chart in a Running Platform
*************************************************

TODO: upload chart via UI

Step 8: Installing and Running the Workflow
*************************************************

TODO: install from extensions view, run via execution, check Airflow UI

Step 9: Debugging the Workflow
*************************************************

TODO: run code-server-chart and set to debug, then access via active applications
TODO: in edk, you can put data inside minio folder and access it via the web interface

Step 10: Advanced Options for Workflow Extensions
*************************************************

TODO: values.yaml that passes values to KaapanaBaseOperator

