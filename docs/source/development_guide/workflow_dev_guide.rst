.. _workflow_dev_guide:

==============================
Developing Workflow Extensions
==============================

Introduction
************
Kaapana is built on technologies that allow many ways of developing workflows for the platform.
Mentioning all of these steps can make the guide difficult to follow, therefore it is restructured with a goal to provide the most straightforward and easy to follow approach to ensure development reproducability in most use cases.
We always appreciate if you reach out to us on Slack if you have any suggestions for improving this document.

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
Everything in this folder is bundled as a Docker container and copied inside the Airflow runtime. Therefore the first file necessary is a :code:`Dockerfile`, but since this container only serves a simple purpose of copying files, it is usually structured the same way in all extensions

.. code-block:: 
    FROM local-only/base-installer:latest // this base image provided by Kaapana is used for copying files inside Airflow 

    # name and version of the image that will be built, tag will look like <registry-url>/dag-otsus-method:0.1.0
    LABEL IMAGE="dag-otsus-method"
    LABEL VERSION="0.1.0"
    # if set to True, the image be ignored by the build script of Kaapana
    LABEL BUILD_IGNORE="False"

    # copy the DAG file to a specific location in base-installer 
    COPY files/dag_otsus_method.py /kaapana/tmp/dags/ 
    # copy two custom operators of the extension in a dir with the name extracted from DAG filename 'dag_<dirname>.py'
    COPY files/otsus-method/OtsusMethodOperator.py /kaapana/tmp/dags/otsus_method/ 
    COPY files/otsus-method/OtsusNotebookOperator.py /kaapana/tmp/dags/otsus_method/

Although some workflow extensions deploy multiple DAGs, (e.g. :code:`nnunet-workflow` which has :code:`nnunet-training`, :code:`nnunet-inference` and :code:`nnunet-ensemble`), it is often the case that a workflow extension has one DAG file.
This guide will focus on the use case where there is a single DAG file for the sake of simplicity, but it should also be obvious to see how multiple DAGs can be provided in a similar way.

The information about DAG definition files can be found in the official Airflow docs. Kaapana DAGs define a custom variable :code:`ui_forms` which specifies the parameters that can be passed from the frontend during the workflow execution.
Following up on the example of the ``otsus-method`` extension, the last part of the `DAG definition file <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/otsus-method/extension/docker/files/dag_otsus_method.py?ref_type=heads#L84>_` can be used as a summary of the DAG:

.. code-block:: python

    get_input >> convert >> otsus_method

    otsus_method >> seg_to_dcm >> dcm_send >> clean
    otsus_method >> generate_report >> put_report_to_minio >> clean


`>>` symbol is used to define execution order of the tasks in the DAG. Every variable is a defined operator that executes a part of the workflow in its own containerized environment and passes the output to the next operator.

.. note::
    Most of the operators used in DAGs are provided by Kaapana for common tasks such as reading data from the PACS or basic conversion tasks (read more: :ref:`operators`).
    Both custom and existing operators should be imported inside DAG files.

Operator files describe an operator class that builds upon KaapanaBaseOperator, which is the common base class for all Kaapana operators. It is responsible for running the container images that are referenced inside operators as Kubernetes objects. Therefore its parameters (see :ref:`operators`) are used to configure the runtime behavior of operators, such as the image to be pulled, memory limits, execution timeout, commands and arguments to run inside containers and more.
The example DAG :code:`otsus-method` contains two custom operators, :code:`OtsusMethodOperator` and :code:`OtsusNotebookOperator`. They both reference images that are defined inside the `processing-containers` directory, which will be explained in the next section.

.. code:: python
    super().__init__(
        dag=dag, # the name of the DAG that this operator belongs to
        name=name, # the name of the operator
        image=f"{DEFAULT_REGISTRY}/otsus-method:{KAAPANA_BUILD_VERSION}", # the image tag that is pulled by the operator. The global variables contain the registry and version that the Kaapana platform has
        image_pull_secrets=["registry-secret"], # the name of the secret that contains the credentials for pulling the image from referenced registry
        execution_timeout=execution_timeout, # the maximum time that the operator is allowed to run
        ram_mem_mb=1000, # the amount of memory that the container will request
        ram_mem_mb_lmt=3000, # the maximum amount of memory that the container is allowed to use
        *args,
        **kwargs,
    )

Note that these parameters can also be passed from the DAG file to the operator as well. It is also possible to define more environment variables for the operator, an example of which can found in another example DAG `Pyradiomics Extractor <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/pyradiomics-feature-extractor/extension/docker/files/pyradiomics_extractor/PyradiomicsExtractorOperator.py?ref_type=heads#L21>_`

This is especially useful for passing values from the workflow execution UI to the DAG, and then to the containers of operators via environment variables.

.. important::
    | The name of the operator file should contain the word "operator" in it, e.g. :code:`OtsusMethodOperator.py` and :code:`OtsusNotebookOperator.py`.
    | This is important for the build script to recognize the file as an operator and automatically build the image that is referenced inside it.

Step 3: Code for Data Processing
*************************************************

``processing-containers`` directory is where the actual code that runs inside the containers pulled by the Airflow operators is stored.
It is possible to have multiple processing containers for multiple operators inside the same extension, but they should be in separate folders.
The example extension ``otsus-method`` has a single processing container, which is defined inside :code:`processing-containers/otsus-method` . It contains a python script :code:`otsus_method.py` where `Otsu's method <https://en.wikipedia.org/wiki/Otsu%27s_method>_` is run on images. There is also one bash scripr and a notebook file for visualizing and generating a report for results of the algorithm.

.. important::
    | The folder structure of the processing container is not important as long as they provide a Dockerfile. Read more about the Docker best practices here: :ref:`how_to_dockerfile` 
    | Although not mandatory, it is strongly recommended to base the container images of processing containers on `local-only/base-python-cpu:latest` or `local-only/base-python-gpu:latest` based on if the algorithm uses GPUs or not. This will allow you to debug inside the containers in Step 9.

It is important to mention here that even though there are two custom operators defined for the DAG, they both reference the same processing container image. The different functionalities are achieved by running different scripts inside the container. 
Inside the DAG definition file, :code:`OtsusNotebookOperator` passes :code:`cmds` and :code:`arguments` parameters to in order to run :code:`run_otsus_report_notebook.sh` inside the container. Whereas :code:`OtsusMethodOperator` does not pass any custom commands, in which case the default run command defined in the Dockerfile :code:`CMD ["python3","-u","/kaapana/app/otsus_method.py"]` is used.

A convention for defining the paths of reading and writing data inside the processing containers is achieved by using common environment variables that are also passed across operators. For example in the :code:`otsus_method.py` script, :code:`"WORKFLOW_DIR"` , :code:`"BATCH_NAME"` , :code:`"OPERATOR_IN_DIR"` and :code:`"OPERATOR_OUT_DIR"` are used to define the input and output paths for the operator.

.. code:: python
    ## Get data from <workflow-dir>/batch folder
    batch_folders = sorted(
        [ f for f in glob.glob(
                os.path.join("/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*")
            )
        ])

    for batch_element_dir in batch_folders:
        element_input_dir = os.path.join(batch_element_dir, os.environ["OPERATOR_IN_DIR"])
        element_output_dir = os.path.join(batch_element_dir, os.environ["OPERATOR_OUT_DIR"])


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

