.. _processing_container_dev_guide:

==================================
Developing a Processing-Container
==================================

A :term:`processing-container` refers to a container image designed to perform data processing tasks.  
These containers are typically executed as part of Workflow tasks, e.g. during data pre-processing, model training, or post-processing steps.

To make the requirements that Kaapana imposes on processing-containers **explicit and standardized**, we developed the **Task API**.
We developed a **Task API** that defines the requirements that Kaapana imposes on a processing-container in an **explicit and standardized** way.
The Task API defines a clear contract between Kaapana and each processing-container.

This contract boils down to a single, simple requirement:

   **A valid processing-container image MUST include a** :file:`processing-container.json` **file that conforms to the JSON schema defined by the Task API at the root of the image.**

When building your Docker image, ensure that the :file:`processing-container.json` file is copied into the image by adding the following line to your :file:`Dockerfile`:

.. code-block:: bash

   COPY files/processing-container.json /processing-container.json


The processing-container.json File
##################################

The :file:`processing-container.json` file defines how Kaapana interacts with a processing-container.  
It describes what the container does, how to configure it, and where input and output data are mounted.

This file is the **only required element** of a valid processing-container image.  
It must conform to the :ref:`processing-container JSON schema <processing-container-schema>`.

A processing-container typically packages a tool or algorithm that may support multiple use cases.  
Each use case is described by a **task template**, which defines input/output channels, environment variables, and the command to execute.


ProcessingContainer
===================

Top-level structure describing the container and its available task templates.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Human-readable name of the processing-container.
   * - ``description``
     - string
     - Short summary of the container’s purpose or functionality.
   * - ``templates``
     - list of :ref:`TaskTemplate`
     - List of available task templates defining different use cases.


TaskTemplate
============

Blueprint describing how the container can be executed for a specific use case.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``identifier``
     - string
     - Unique name identifying the task template; used by users or workflows to select it.
   * - ``description``
     - string
     - Explains what this task template does and how it processes data.
   * - ``inputs``
     - list of :ref:`IOMount`
     - Defines where and how input data is mounted into the container.
   * - ``outputs``
     - list of :ref:`IOMount`
     - Defines output directories for results produced by the process.
   * - ``env``
     - list of :ref:`TaskTemplateEnv`
     - Environment variables that configure the behavior of the container.
   * - ``command`` *(optional)*
     - list of strings
     - Command executed inside the container. If omitted, the image’s default command is used.
   * - ``resources`` *(optional)*
     - :ref:`Resources`
     - CPU, memory, and GPU requests and limits for container execution.


TaskTemplateEnv
===============

Defines configurable environment variables for a task template.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Name of the environment variable.
   * - ``value``
     - string
     - Default value used if not overridden.
   * - ``type`` *(optional)*
     - enum (``boolean``, ``string``, ``int``)
     - Data type of the variable.
   * - ``choices`` *(optional)*
     - list of strings
     - List of allowed values.
   * - ``adjustable`` *(optional)*
     - boolean
     - Whether users may modify this variable at runtime.
   * - ``description`` *(optional)*
     - string
     - Explains how the variable influences processing.


IOMount
=======

Defines a data channel (input or output) and where it is mounted inside the container.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Unique name identifying the channel.
   * - ``mounted_path``
     - string
     - Path inside the container where the channel data is available.
   * - ``description`` *(optional)*
     - string
     - Short explanation of the channel’s purpose or data type.
   * - ``scale_rule`` *(optional)*
     - :ref:`ScaleRule`
     - Defines how resources scale with the size of data in this channel.


ScaleRule
=========

Controls how container resources (CPU/memory) scale with input data size.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``complexity``
     - string (pattern: ``^[-+]?\\d*(\\.\\d+)?\\*?n(\\*\\*\\d+)?$``)
     - Mathematical expression describing how resource use grows with input size.
   * - ``type``
     - enum (``limit``, ``request``)
     - Resource type affected by the rule.
   * - ``mode``
     - enum (``sum``, ``max_file_size``)
     - How to aggregate file sizes for scaling.
   * - ``target_dir`` *(optional)*
     - string
     - Directory to analyze for scaling (defaults to channel root).
   * - ``target_regex`` / ``target_glob`` *(optional)*
     - string
     - File-matching pattern for selective scaling.


Resources
=========

Specifies resource requests and limits for container execution.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``limits``
     - object *(optional)*
     - Maximum resources (CPU, memory, GPU) available to the container.
   * - ``requests``
     - object *(optional)*
     - Minimum guaranteed resources for scheduling.


Example
=======

.. code-block:: json

   {
     "name": "my_algorithm",
     "description": "Example processing-container for demonstration",
     "templates": [
       {
         "identifier": "default",
         "description": "Performs example data processing.",
         "inputs": [],
         "outputs": [
           {"name": "channel1", "mounted_path": "/home/channel1"},
           {"name": "channel2", "mounted_path": "/home/channel2"}
         ],
         "env": [
           {
             "name": "TIME_SLEEP",
             "value": "5",
             "type": "int",
             "description": "Number of seconds to sleep before finishing.",
             "adjustable": true
           }
         ],
         "command": ["python3", "-u", "start.py"]
       }
     ]
   }



The Task API Command Line Interface (CLI)
#########################################

The Task API provides a Python-based Command Line Interface (CLI) that allows you to **run and test processing-containers locally using Docker**. 
No running Kaapana platform is required.

Installation
============

The CLI is included in the `task-api` package, which can be installed directly from the Kaapana repository using :ref:`pip`:

.. code-block:: bash

    python3 -m pip install "task-api@git+https://codebase.helmholtz.cloud/kaapana/kaapana.git@develop#subdirectory=lib/task_api"

Validating a ``processing-container.json`` File
===============================================

You can easily verify whether your :code:`processing-container.json` file conforms to the required JSON schema using the following command:

.. code-block:: bash

    python3 -m task_api.cli validate processing-container.json --schema pc

Running a Task Locally with Docker
==================================


To execute a task locally, you need a :file:`task.json` file describing **how a TaskTemplate is instantiated**, including input/output bindings, environment variables, and execution parameters.

Required fields in the :file:`task.json` file:

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Human-readable name for this task execution.
   * - ``image``
     - string
     - Docker image of the processing-container to run.
   * - ``taskTemplate``
     - string or object (:ref:`TaskTemplate`)
     - Identifier or full definition of the task template to execute.
   * - ``inputs``
     - array of :ref:`IOVolume`
     - Input channels mapped to local directories.
   * - ``outputs``
     - array of :ref:`IOVolume`
     - Output channels mapped to local directories where results are written.
   * - ``env`` *(optional)*
     - array of :ref:`BaseEnv`
     - Environment variables to override template defaults.
   * - ``command`` *(optional)*
     - array of strings
     - Overrides the default container command or task template command.
   * - ``resources`` *(optional)*
     - :ref:`Resources`
     - Resource requests and limits (CPU, memory, GPU) for this task.
   * - ``config`` *(optional)*
     - :ref:`DockerConfig` or :ref:`BaseConfig`
     - Container runtime configuration (e.g., Docker labels).

Inputs and Outputs: IOVolume
----------------------------

Each input or output channel is represented by an :ref:`IOVolume` object, which defines the channel name, the local path to mount, and optional scaling rules.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Unique name of the input/output channel.
   * - ``input``
     - oneOf: [HostPathVolume]
     - Volume to mount into the processing-container
   * - ``input.host_path``
     - string
     - Local directory path on the host that is mounted into the container.
   * - ``scale_rule`` *(optional)*
     - :ref:`ScaleRule`
     - Defines how container resources (memory/CPU) should scale with input data size.

.. note::
    
    For output channels, the ``input`` field represents the path where results will be written.


Validating the Task JSON
-------------------------

Before execution, ensure your :file:`task.json` file is compliant with the schema:

.. code-block:: bash

    python3 -m task_api.cli validate task.json --schema task


Executing the Task
------------------

Run the task locally via Docker:

.. code-block:: bash

    python3 -m task_api.cli run task.json --mode docker

This creates a file :file:`task_run-<id>.pkl` in the current working directory.  
You can use this file to access logs or perform follow-up operations:

.. code-block:: bash

    python3 -m task_api.cli logs task_run-<id>.pkl

Example
-------

A minimal example :file:`task.json` for local execution:

.. code-block:: json

    {
      "name": "example-task",
      "image": "kaapana/example:latest",
      "taskTemplate": "example",
      "inputs": [
        {"name": "channel1", "input": {"host_path": "./data/input1"}},
        {"name": "channel2", "input": {"host_path": "./data/input2"}}
      ],
      "outputs": [
        {"name": "results", "input": {"host_path": "./data/output"}}
      ],
      "env": [
        {"name": "DUMMY", "value": "5"}
      ]
    }

This file binds input/output directories, sets environment variables, and selects the task template to run.


.. note::
    To explore all available commands and options, run:

    .. code-block:: bash

        python3 -m task_api.cli --help


.. _data_structure_convention:

Input and output channel data structure convention
###################################################

When data is passed from one task-run to another task-run,
the data structure of the output channel has to match the expectations of the respective input channels.
Therefore, we propose a conventional data structure for output channels.
We assume, that any channel contains results for 1 to N items.
Then we expect the output channel to have the following structure

.. code:: bash
    
    └── output-mount-path
        ├── item-1-identifier
        │   └── result
        ├── item-2-identifier
        │   └── result
        ├── ...
        └── item-N-identifier
            └── result

For processes that create results for each input item we expect, that item-identifiers of the output channel match the corresponding identifier from the input channel.

.. code:: bash
    
    └── input-mount-path
    │   ├── item-1-identifier
    │   │   └── input
    │   └── item-2-identifier
    │       └── input
    └── output-mount-path
        ├── item-1-identifier
        │   └── result
        └── item-2-identifier
            └── result

For processes that create a results on multiple items of an input-channel we expect an output channel with a single item.
The result-identifier should be different from input item identifiers.


.. code:: bash
    
    └── input-mount-path
    │   ├── item-1-identifier
    │   │   └── input
    │   └── item-2-identifier
    │       └── input
    └── output-mount-path
        └── result-identifier
            └── result


.. note::

    We strongly advise to use the description to specify which data structure is expected and can be exptected per input and output channel.


Using a processing-container in an Airflow DAG
###############################################

To use a processing-container in an Airflow DAG it is necessary, that you have build the container image and pushed it to the default registry of your Kaapana platform.

For using a processing-container in an Airflow DAG we provide a dedicated :code:`KaapanaTaskOperator`.
So you don't have to write a dedicated Airflow operator anymore.

Currently, you have to install the `task-api-workflow` extension in your Kaapana platform to make this operator available.

The following is a minimal example for a DAG that consists of a single operator

.. code:: python

    from airflow.models import DAG
    from task_api_operator.KaapanaTaskOperator import KaapanaTaskOperator
    from kaapana.blueprints.kaapana_global_variables import (
        DEFAULT_REGISTRY,
        KAAPANA_BUILD_VERSION,
    )

    args = {
        "ui_visible": True,
        "owner": "kaapana",
    }

    with DAG("my-dag", default_args=args) as dag:
        my_task = KaapanaTaskOperator(
            task_id="my-task",
            image=f"{DEFAULT_REGISTRY}/<container-image>:{KAAPANA_BUILD_VERSION}",
            taskTemplate="my-tasktemplate-identifier",
        )

The :code:`KaapanaTaskOperator` requires at least three parameters to be set:

* :code:`task_id`: A unique name for the task in your DAG.
* :code:`image`: The container image of your processing-container which you pushed to the default registry of your Kaapana platform.
* :code:`taskTemplate`: The identifier of the task template that is specified in the :code:`processing-container.json` file in the container image.

Optional parameters allow you to overwrite environment variables and the command that is executed in the processing-container.


Passing data between operators
------------------------------

For passing data between two operators you have to set the parameter :code:`iochannel_maps` for the :code:`KaapanaTaskOperator:`.

Assume, you want to create a relatively simple workflow that consists of three tasks:

* **Task 1**: Based on the container image :code:`my-download` and the task template :code:`download-from-url`. It downloads data from an url into the output channel :code:`downloads`.
* **Task 2**: Based on the container image :code:`my-processing` and task template :code:`my-agorithm`. It processes all files in its input channel :code:`inputs` creates results and stores them in the output channel :code:`outputs`.
* **Task 3**: Based on the container image :code:`my-upload` and task template :code:`send-to-minio`. It sends all files in its input channel `inputs` to a Minio bucket.

In the parameter :code:`iochannel_maps` we can specify, which output channel should be mapped to which input channel.


.. code:: python

    from airflow.models import DAG
    from task_api_operator.KaapanaTaskOperator import KaapanaTaskOperator, IOMapping
    from kaapana.blueprints.kaapana_global_variables import (
        DEFAULT_REGISTRY,
        KAAPANA_BUILD_VERSION,
    )

    args = {
        "ui_visible": True,
        "owner": "kaapana",
    }

    with DAG("test-task-operator", default_args=args) as dag:
        download = KaapanaTaskOperator(
            task_id="get-data",
            image=f"{DEFAULT_REGISTRY}/my-get-data:{KAAPANA_BUILD_VERSION}",
            taskTemplate="download-from-url",
        )

        processing = KaapanaTaskOperator(
            task_id="process-data",
            image=f"{DEFAULT_REGISTRY}/my-processing:{KAAPANA_BUILD_VERSION}",
            taskTemplate="my-algorithm",
            iochannel_maps=[
                IOMapping(
                    upstream_operator=task1,
                    upstream_output_channel="downloads",
                    input_channel="inputs",
                )
            ],
        )

        upload = KaapanaTaskOperator(
            task_id="upload-data",
            image=f"{DEFAULT_REGISTRY}/my-upload:{KAAPANA_BUILD_VERSION}",
            taskTemplate="send-to-minio",
            iochannel_maps=[
                IOMapping(
                    upstream_operator=task2,
                    upstream_output_channel="results",
                    input_channel="inputs",
                )
            ],
        )

    download >> processing >> upload


You can find a hello-world example DAG that consists of two tasks here: TODO


Passing user configuration to a task-run
-----------------------------------------

A common requirement for workflows is, that users are able to make configurations to the processing of the data.
This configuration has to be passed to the process that is running inside the processing-containers.

Workflows are triggered via requests to the Airflow Rest API.
The payload of this request contains a :code:`conf` object, which is available to the :code:`KaapanaTaskOperator`.
You can configure environment variables in :code:`conf` at :code:`conf.task_form.{TASK_ID}.{VAR_NAME}.{VAR_VALUE}`
An example request to the Airflow Rest API to trigger a Workflow with custom configuration can look like this:

.. code:: bash

    curl -X 'POST' \
    'https://{KAAPANA_DOMAIN}/flow/api/v1/dags/{dag_id}/dagRuns' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "dag_run_id": "<unique_dag_run_id>",
    "conf": {
        "task_form": {
            "{TASK_ID}": {
                "{VAR_NAME}": "{VAR_VALUE}" 
                }
            }
        }
    }'

This will pass the environment variable :code:`MY_VAR=MY_VAR_VALUE` to the container for the task_id :code:`TASK_ID` in the dag with dag-id :code:`dag_id`.

.. note::

    The order of precedence for environment variables is as follows:
    conf.task_form.env >> KaapanaTaskOperator.env >> processing-container.task-template.env 


Container images from another registry
----------------------------------------
In case you want to use a container image from another registry than the default registry, you can set the parameters :code:`registryUrl`, :code:`registryUsername`, :code:`registryPassword`.
This will create a dedicated registry secret for this task.



Migrating from KaapanaBaseOperator
####################################


This section will explain how to migrate the processing-container that was used in combination with an Airflow operator
which inerhited from the :code:`KaapanaBaseOperator` to a processing-container that can be used with the KaapanaTaskOperator.


Implicit conventions from the KaapanaBaseOperator
---------------------------------------------------

The :code:`KaapanaBaseOperator` has several implicit conventions that had to be considered, when implementing the processing-container, i.e. 

* Files are mounted into the same location for each processing-container.
* File locations have to be determined from generic environment variables.
* The generic environment variables are set automatically by the :code:`KaapanaBaseOperator`.
* Environment variables are globally set for all tasks in a workflow.

The :code:`KaapanaTaskOperator` will not automatically set the necessary environment variables to generate the same file paths as before.


.. list-table::
    :header-rows: 1

    *   - :code:`KaapanaBaseOperator`
        - :code:`KaapanaTaskOperator`
    *   - All workflow directories are mounted into the container.
        - Only input and output channels are mounted into the container.
    *   - File paths have to be constructed from environment variables.
        - File paths are always relative to :code:`mount_path` of the corresponding channel.
    *   - Environment variables for file path construction are set automatically.
        - No additional environment variables are set.
    *   - Variables in the :code:`conf` are shared between all containers in a workflow-run.
        - Variables in the :code:`conf` are task-run specific.

The biggest change is how data is mounted into the container.
If you use the KaapanaBaseOperator, every container will see a directory structure similar to

Assume you have the following DAG definition

.. code:: python

    dag = DAG(dag_id="my_dag")

    get_input = GetInputOperator(dag=dag)
    my_algorithm = MyAlgorithmOperator(dag=dag, input_operator=get_input)

    get_input >> my_algorithm


Then Kaapana would automatically set the environment variables :code:`WORKFLOW_DIR`, :code:`BATCH_NAME`, :code:`OPERATOR_IN_DIR` and :code:`${OPERATOR_OUT_DIR}`.
Additionally, Kaapana would automatically mount the following directory structure in the container of the task-run of :code:`my_algorithm`

.. code:: bash

    └── ${WORKFLOW_DIR}
        ├── ${BATCH_NAME}
        │   ├── item-1
        │   │   └── ${OPERATOR_IN_DIR}
        │   │       └── input
        │   └── item-2
        │       └── ${OPERATOR_IN_DIR}
        │           └── input
        └── conf
            └── conf.json

It is expected, that :code:`my_algorithm` follows this convention. Hence, the final directory strucutre would look like this

.. code:: bash

    └── ${WORKFLOW_DIR}
        ├── ${BATCH_NAME}
        │   ├── item-1
        │   │   ├── ${OPERATOR_IN_DIR}
        │   │   │   └── input
        │   │   └── ${OPERATOR_OUT_DIR}
        │   │       └── result
        │   └── item-2
        │       ├── ${OPERATOR_IN_DIR}
        │       │   └── input
        │       └── ${OPERATOR_OUT_DIR}
        │           └── result
        └── conf
            └── conf.json


Migrating the data structure
------------------------------

The DAG from above migrated to using the KaapanaTaskOperator could look like this:

.. code:: python

    with DAG("my_dag", default_args=args) as dag:
        get_input = KaapanaTaskOperator(
            task_id="get_input",
            image=f"{DEFAULT_REGISTRY}/get-input:{KAAPANA_BUILD_VERSION}",
            taskTemplate="dicom",
        )

        my_algorithm = KaapanaTaskOperator(
            task_id="my_algorithm",
            image=f"{DEFAULT_REGISTRY}/my-algorithm:{KAAPANA_BUILD_VERSION}",
            taskTemplate="my-algorithm",
            iochannel_maps=[
                IOMapping(
                    upstream_operator=get_input,
                    upstream_output_channel="downloads",
                    input_channel="inputs",
                )
            ],
        )


    get_input >> my_algorithm

Following the :ref:`data structure convetion <data_structure_convention>`, the directory structure in the processing-container of :code:`my_algorithm` should look like this:

.. code:: bash
    
    └── input-mount-path
    │   ├── item-1
    │   │   └── input
    │   └── item-2
    │       └── input
    └── output-mount-path
        ├── item-1
        │   └── result
        └── item-2
            └── result




Features not supported by the KaapanaTaskOperator
--------------------------------------------------

Some features, that are supported in the KaapanaBaseOperator are not supported in the KaapanaTaskOperator:

* The `kaapanapy` package does not work out of the box, because expected environment variables are not automatically set.
* The :code:`conf` object is not mounted into the container.
* Starting a code-server as development server.
* ui_forms: data_form, workflow_form