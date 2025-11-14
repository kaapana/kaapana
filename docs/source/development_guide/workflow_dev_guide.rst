.. _workflow_dev_guide:

==============================
Developing Workflow Extensions
==============================

Introduction
************
Kaapana is built on technologies that allow many ways of developing workflows for the platform.
Although there are multiple ways to develop Kaapana workflows, this guide will follow the most commonly applicable and recommended way.
We always appreciate if you reach out to us on `Slack <https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ/>`_ if you have any suggestions for improving this document.

When possible, there will still be multiple options in separate tabs for completing some steps below.
However, if you are not sure about an advanced option, proceed with the one in the leftmost tab as this should work in most scenarios.

.. important:: 
    | This guide assumes that:
    |
    | 1. You already have a running Kaapana platform with admin access
    | 2. You have a basic understanding of the Kaapana platform and its components, if not please refer to the :ref:`user_guide`
    | 3. You have access to a terminal where the platform is running (if you are using EDK, you can skip this step)
    | 4. You have a local development environment with access to internet, you have either Docker or Podman installed, and you cloned the `Kaapana repository <https://codebase.helmholtz.cloud/kaapana/kaapana/-/tree/master>`_ (if you are using EDK, you can skip this step)

    If you do not have an access to a terminal where Kaapana is deployed, you can still use EDK (Extension Development Kit) :ref:`extensions_edk` inside the platform directly.
    For that, the Kaapana version should be at least :code:`0.4.0` , and there needs to be internet access on the machine where it is deployed.
    You can reach out to us on Slack if you do not satisfy these conditions.


Throughout this guide, a simple workflow extension called ``otsus-method`` will be used as example. You can find the code in the `templates_and_examples folder in the Kaapana repository <https://codebase.helmholtz.cloud/kaapana/kaapana/-/tree/develop/templates_and_examples/examples/processing-pipelines/otsus-method>`_ .

Kaapana has a convention for the folder structure of extensions, which is recognized by other internal tools such as the build script. Therefore it is important to know what each directory contains.
The folder structure of the example ``otsus-method`` extension is as follows:

.. code-block::

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

``extension/otsus-method-workflow`` directory contains everything regarding the configuration of the Helm chart, which is used to deploy the workflow. The naming of this folder is arbitrary and is not referenced anywhere else.
This usually only includes files expected by Helm, such as ``Chart.yaml``, ``values.yaml``, ``requirements.yaml``, ``README.md`` and sometimes a ``templates`` directory. More details about these files can be found in the `Helm documentation <https://helm.sh/docs/topics/charts/>`_.

For a custom workflow extension, the following should be ensured inside the ``extension/otsus-method-workflow`` directory:

.. tabs::

      .. tab:: Local Dev
        
        1. ``Chart.yaml`` is filled with the correct information about your extension, see the `Helm Chart documentation <https://helm.sh/docs/topics/charts/#the-chartyaml-file>`_ and the example `otsus-method-workflow Chart.yaml <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/otsus-method/extension/otsus-method-workflow/Chart.yaml?ref_type=heads>`_
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
Everything in this folder is bundled as a Docker container and copied inside the Airflow runtime. A standardized and simple :code:`Dockerfile` is used for this purpose:

.. code-block:: bash

    FROM local-only/base-installer:latest // this base image provided by Kaapana is used for copying files inside Airflow 

    # name and version of the image that will be built, tag will look like <registry-url>/dag-otsus-method:0.1.0
    LABEL IMAGE="dag-otsus-method"
    LABEL VERSION="0.1.0"
    # if set to True, the image be ignored by the build script of Kaapana
    LABEL BUILD_IGNORE="False"

    # copy the DAG file to a specific location in base-installer 
    COPY files/dag_otsus_method.py /kaapana/tmp/dags/ 
    # copy two custom operators of the extension in a dir with the name extracted from DAG filename 'dag_<dirname>.py'
    COPY files/otsus-method/OtsusMethodOperator.py /kaapana/tmp/dags/otsus_method/ 
    COPY files/otsus-method/OtsusNotebookOperator.py /kaapana/tmp/dags/otsus_method/

Although some workflow extensions deploy multiple DAGs (e.g. :code:`nnunet-workflow`), it is often the case that a workflow extension has one DAG file.
This guide will focus on the use case where there is a single DAG file for the sake of simplicity. For an extension with multiple DAGs, see `nnunet-workflow <https://codebase.helmholtz.cloud/kaapana/kaapana/-/tree/develop/data-processing/processing-pipelines/nnunet/extension/docker/files>`_.

The information about DAG definition files can be found in the official Airflow docs. Kaapana DAGs define a custom variable :code:`ui_forms` which specifies the parameters that can be passed from the frontend during the workflow execution.
Following up on the example of the ``otsus-method`` extension, the last part of the `DAG definition file <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/otsus-method/extension/docker/files/dag_otsus_method.py?ref_type=heads#L84>`_ can be used as a summary of the DAG:

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

It is also possible to define more environment variables for operators. This can be seen in another example DAG `Pyradiomics Extractor <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/pyradiomics-feature-extractor/extension/docker/files/dag_pyradiomics_extract_features.py?ref_type=heads#L71>`_ where the operator then `fetches <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/pyradiomics-feature-extractor/extension/docker/files/pyradiomics_extractor/PyradiomicsExtractorOperator.py?ref_type=heads#L21>`_ the value that the user `provided in ui forms <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/processing-pipelines/pyradiomics-feature-extractor/extension/docker/files/dag_pyradiomics_extract_features.py?ref_type=heads#L22>`_.

This is especially useful for passing values from the workflow execution UI to the DAG, and then to the containers of operators via environment variables.

.. important::
    | The name of the operator file has to contain the word "operator" in it, e.g. :code:`OtsusMethodOperator.py` and :code:`OtsusNotebookOperator.py`.
    | This is important for the build script to recognize the file as an operator and automatically build the image that is referenced inside it.

Step 3: Code for Data Processing
*************************************************

``processing-containers`` directory is where the actual code that runs inside the containers pulled by the Airflow operators is stored.
It is possible to have multiple processing containers for multiple operators inside the same extension, but they should be in separate folders.
The example extension ``otsus-method`` has a single processing container, which is defined inside :code:`processing-containers/otsus-method`. 
It contains a python script :code:`otsus_method.py` where `Otsu's method <https://en.wikipedia.org/wiki/Otsu%27s_method>`_ is run on images. There is also one bash scripr and a notebook file for visualizing and generating a report for results of the algorithm.

.. important::
    | The structure of the processing container should be 1. a :code:`Dockerfile` and 2. a :code:`files` directory where the source code and other files are stored. Read more about the Docker best practices here: :ref:`how_to_dockerfile` 
    | Although not mandatory, it is strongly recommended to base the container images of processing containers on `local-only/base-python-cpu:latest` or `local-only/base-python-gpu:latest` based on if the algorithm uses GPUs or not. This will allow you to debug inside the containers in Step 9.

.. TODO: when the kaapanapy is documented, also mention above that users can not access kaapanapy without the base image 

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

So far we have defined the Helm chart for kubernetes objects, a container image for Airflow configuration files and another image for the processing container. The next step is to build the chart and the containers, and access them inside the platform. We will first start with the containers.


.. tabs::

      .. tab:: Local Dev

        | **1.** build 3 base images from the Kaapana repository: :code:`base-python-cpu, base-python-gpu, base-installer`. This can be done in two ways:
        | **1.a.** either running the build script :code:`cd <path-to-kaapana-repo>/build-scripts && python3 start_build.py` , however it also builds all the other images inside the platform so it can take some more time and storage space.
        | **1.b.** or building each image script for each image separately: 
        | - :code:`$ cd <path-to-kaapana-repo>`
        | - :code:`$ docker/podman build -t local-only/base-python-cpu:latest data-processing/base-images/base-python-cpu`
        | - :code:`$ docker/podman build -t  local-only/base-python-gpu:latest data-processing/base-images/base-python-gpu` 
        | - :code:`$ docker/podman build -t local-only/base-installer:latest services/utils/base-installer`
        | **2.** from the about section in your platform, get the registry URL and the platform version
        | **3.** build the Airflow DAG image: :code:`docker/podman build -t <platform-registry-url>/<dag-name>:<platform-version> <path-to-extension>/extension/docker`
        | **4.** build all processing containers :code:`docker/podman build -t <platform-registry-url>/<processing-container-name>:<platform-version> <path-to-extension>/processing-containers/<processing-container-name>`

      .. tab:: EDK

        | **1.** run :code:`./init.sh` script inside the EDK code server path :code:`/kaapana/app`. This will build all base images and push them to the local registry
        | **2.** copy your extension folder inside the :code:`/kaapana/app/kaapana/extensions` directory
        | **3.** run :code:`./build_extension.sh --dir /kaapana/app/dag/<path-to-extension>`
        | **4.** you should be able to see the built images for your extension via the local-registry-ui, which can be accessed via the link next to the EDK extension in extensions view
        | 
        | It is highly recommended to read the scripts inside EDK if you want to customize (e.g. build another base image if you are using one) or optimize (e.g. remove building unused base images if you don't need them)

.. important::
    | If you used EDK for this step, you can skip directly to Step 8

.. note::
    | The `base-python-gpu` image is only required for GPU-dependent extensions and can be omitted if your extension does not use GPU functionality.


Step 5: Putting Containers in a Running Platform
************************************************

Now that we have built the containers, we need to put them in a running platform. 

.. tabs::

      .. tab:: Local Dev with write access to Registry

        | **1.** push all images to the registry: 
        | - :code:`docker/podman push <platform-registry-url>/<dag-name>:<platform-version>` 
        | - :code:`docker/podman push <platform-registry-url>/<processing-container-name>:<platform-version>`

      .. tab:: Local Dev without write access to Registry

        | **1.** save all images that you built in an :code:`images.tar` file:
        | - :code:`docker/podman save <platform-registry-url>/<dag-name>:<platform-version> <platform-registry-url>/<processing-container-name>:<platform-version> -o images.tar`
        | Add all of the processing containers you have to the list of images in the command before :code:`-o images.tar` part. This step will take some time depending on the size of images and number of processing containers
        | **2.** go to the extensions view in the platform UI and upload the :code:`images.tar` file via the `Upload chart or container files` section. This upload will also take some time depending on the size of the images

        If 2nd step fails for any reason, make sure to check the FAQ of the documentation: :ref:`extension_container_upload_fail`

Step 6: Packaging the Helm Chart
*************************************************

| So far we have built all the necessary images and made them available in the platform. The only thing left is to package the Helm chart and upload it to the platform so that the extension can be installed and tested. 
| For the local dev case, you need to run :code:`cd <path-to-extension>/extension/otsus-method-workflow && helm dep up && helm package .` . This will create a :code:`otsus-method-workflow-<version>.tgz` file in the same directory.

.. note::
    Verify that all file paths are correct and that the versions used are consistent.


Step 7: Putting the Chart in a Running Platform
*************************************************

For the local dev case, you can upload the :code:`otsus-method-workflow-<version>.tgz` file to the platform via the extensions view in the UI. This should happen pretty quickly, but in case it fails check the FAQ of the documentation: :ref:`extension_chart_upload_fail`

Step 8: Installing and Running the Workflow
*************************************************

Now that we have the whole extension inside the platform, it can be installed from the extension view and can be run from the workflow execution or Datasets view.

.. important::
    | Starting from version :code:`0.5.0`, new extensions in the platform should be explicitly allowed in projects. Go to System/Projects view, select the project you want to use the extension in and use "Add Software to Project" button.

.. note::
    | After installing the extensions, if there is an :code:`ErrImagePull` or :code:`ImagePullBackOff` error, this means that the DAG image referenced inside the Kubernetes objects created by the Helm chart. This can happen if:
    | **1.** the image name is referenced incorrectly in the :code:`values.yaml` of the Helm chart
    | **2.** the registry URL or version is incorrect in the images that are built. You can check whihch image is being pulled by going to the Kubernetes view in the platform UI and looking for the pod that has :code:`<dag-name>` (e.g. for our example extension : :code:`dag-otsus-method`). Look for the error message in this view and ensure if the referenced image is correct
    | **3.** if you pushed the containers to the platform via the upload UI, follow the steps in this FAQ: :ref:`extension_container_upload_fail`

.. hint::
   | Workflows built this way are marked as **experimental**.
   | By default, **experimental** extensions are hidden. To view them, select **Experimental** in the **Maturity** filter under the Extensions tab.

Step 9: Debugging the Workflow
*************************************************
After running the workflow, if any jobs is shown as failed inside the Workflow List view, Kaapana provides a way to debug the workflow via opening a code-server environment inside container of the failed operator.

1. find out which operator has failed, which can be done by checking the logs of the failed job. This should lead you to the logs of the operator that has failed.
2. go to the extensions view, and click on the link next to the :code:`code-server-chart` (renamed as :code:`Code Server for Airflow` in versions >= 0.5.0)
3. open the DAG file :code:`/kaapana/mounted/workflows/dags/<your-dag-definition-file>.py` and go to where the operator is defined
4. add a parameter :code:`dev_server="code-server"` (you can also add a :code:`display_name` for versions >= 0.5.0)  
5. head to the :code:`Active Applications` view and open the link to the code-server application of this operator
6. you should be able to see the code of the container that the operator pulls, i.e. the code in :code:`processing-container` and you can run and debug it directly on the data

.. important::
    | This debug option can also be used for developing better processing scripts and testing if the file paths and environment variables are set correctly

Step 10: Advanced Options for Workflow Extensions
*************************************************

You can add a custom extension parameter to the :code:`values.yaml` file which can then be passed to different operators inside the DAG. For an example of it see `Total Segmentator workflow <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/data-processing/processing-pipelines/total-segmentator/extension/total-segmentator-workflow/values.yaml?ref_type=heads>`_ . You can read more about extension parameters in the :ref:`extensions` section.


**Automatic Metric Scraping**:
You can enable automatic metric scraping by adding annotations to the Operator inheriting from KaapanaBaseOperator. Annotations are identical to the ones in :ref:`application_dev_guide`. Keep in mind that this only makes sense if a compatible metrics endpoint is exposed from within the running container.
Annotations can be added either **(a)** in the Operator definition or **(b)** in the DAG when instantiating the Operator.



Example from the otsus-method example from ``kaapana/templates_and_examples/examples/processing-pipelines/otsus-method/extension/docker/files/otsus-method/OtsusMethodOperator.py`` (this pod does not expose a metrics endpoint, but we use it as an example for how annotations can be added in the Operator definition):

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
            execution_timeout=execution_timeout,
            # operator_out_dir="otsus-method/",
            annotations={
                "prometheus.io/scrape": "true",
                "prometheus.io/port": "1234",
                "prometheus.io/path": "/metrics",
                "prometheus.io/scheme": "http",
                "prometheus.io/custom_job_name": "OtsusMethodOperator",
            },
            *args,
            **kwargs,
        )   

Example from the otsus-method example from ``kaapana/templates_and_examples/examples/processing-pipelines/otsus-method/extension/docker/files/dag_otsus_method.py`` (the GetInputOperator does also not expose a metrics endpoint, but we use it as an example for how annotations could be added to any Operator inheriting from KaapanaBaseOperator in the DAG definition):

.. code-block:: python
    
    # [...]
    dag = DAG(dag_id="otsus-method", default_args=args, schedule_interval=None)


    get_input = GetInputOperator(
        dag=dag,
        annotations={
            "prometheus.io/scrape": "true",
            "prometheus.io/port": "1234",
            "prometheus.io/path": "/metrics",
            "prometheus.io/scheme": "http",
            "prometheus.io/custom_job_name": "dag_otsus_method_GetInputOperator",
        },
    )
    # [...]

This will enable Prometheus auto-discovery to automatically find and scrape the configured endpoint when the pod of the Operator is running.