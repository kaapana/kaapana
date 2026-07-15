.. _workflow_development:

====================
Workflow Development
====================

Kaapana uses `Apache Airflow <https://airflow.apache.org/>`_ as its workflow engine to orchestrate the execution of processing pipelines.
Every workflow available in Kaapana is implemented as an Airflow DAG (Directed Acyclic Graph), where each node in the DAG represents a task that typically runs a processing-container.
When a user triggers a workflow, e.g. from the Kaapana UI, this starts a DAG run, which executes the individual tasks according to the dependencies defined in the DAG.

Using a processing-container in an Airflow DAG
###############################################

To use a processing-container in an Airflow DAG, you first need to **build the container image** and push it to the default registry of your Kaapana platform.

We provide a dedicated :code:`KaapanaTaskOperator` so that you **do not need to implement a custom Airflow operator** for each container.

.. note:: 
  
  You must install the `task-api-workflow` extension on your Kaapana platform to make this operator available.

Minimal DAG Example
===================

The following is a minimal DAG with a single task:

.. code:: python

    from airflow.models import DAG
    from task_api_operators.KaapanaTaskOperator import KaapanaTaskOperator
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

The :code:`KaapanaTaskOperator` takes these parameters:

.. list-table::
  :header-rows: 1

  * - Field
    - Type
    - Description
  * - :code:`task_id`
    - string 
    - Unique name of the task in the DAG.
  * - :code:`image`
    - string 
    - Container image of your processing-container (pushed to the default registry).
  * - :code:`taskTemplate`
    - string/taskTemplate
    - Identifier of the task template defined in the :code:`processing-container.json` file inside the container image.
  * - :code:`env` (optional)
    - list[dict]
    - List key-value pairs for overriding environment variables.
  * - :code:`command` (optional)
    - list
    - Command to execute instead of the default command.
  * - :code:`iochannel_maps` (optional)
    - list[IOMapping]
    - List of mappings from upstream operators output channels to input channels


Passing data between operators
===============================

To connect outputs of one task to inputs of another, use the :code:`iochannel_maps` parameter of the :code:`KaapanaTaskOperator`.
The parameter :code:`iochannel_maps` expects a list of :code:`IOMapping` objects, which requires the following arguments:

.. list-table::
  :widths: 25 75
  :header-rows: 1

  * - **Name**
    - **Description**
  * - ``upstream_operator``
    - The upstream Airflow task whose output is being used.
      This defines the task that produces the data for the downstream input.
  * - ``upstream_output_channel``
    - The name of the output channel of the task template used in the upstream task.
      Identifies which output of the upstream task should be connected.
  * - ``input_channel``
    - The name of the input channel of the task template used in this task.
      Determines where the data will be received.

As an example take a workflow that consists of the following three tasks:

1. **Task GetInput:** Downloads data using container :code:`my-download` and task template :code:`download-from-url`. Output channel: :code:`downloads`.  
2. **Task Process:** Processes data using container :code:`my-processing` and task template :code:`my-algorithm`. Reads from input channel :code:`data-to-process` and writes to output channel :code:`processed-data`.  
3. **Task Upload:** Uploads results using container :code:`my-upload` and task template :code:`send-to-minio`. Reads from input channel :code:`data-for-upload`.

The DAG file would look like this

.. code:: python

    from airflow.models import DAG
    from task_api_operators.KaapanaTaskOperator import KaapanaTaskOperator, IOMapping
    from kaapana.blueprints.kaapana_global_variables import (
        DEFAULT_REGISTRY,
        KAAPANA_BUILD_VERSION,
    )

    args = {
        "ui_visible": True,
        "owner": "kaapana",
    }

    with DAG("my-dag", default_args=args) as dag:
        GetInput = KaapanaTaskOperator(
            task_id="get-data",
            image=f"{DEFAULT_REGISTRY}/my-get-data:{KAAPANA_BUILD_VERSION}",
            taskTemplate="download-from-url",
        )

        Process = KaapanaTaskOperator(
            task_id="process-data",
            image=f"{DEFAULT_REGISTRY}/my-processing:{KAAPANA_BUILD_VERSION}",
            taskTemplate="my-algorithm",
            iochannel_maps=[
                IOMapping(
                    upstream_operator=GetInput,
                    upstream_output_channel="downloads",
                    input_channel="data-to-process",
                )
            ],
        )

        Upload = KaapanaTaskOperator(
            task_id="upload-data",
            image=f"{DEFAULT_REGISTRY}/my-upload:{KAAPANA_BUILD_VERSION}",
            taskTemplate="send-to-minio",
            iochannel_maps=[
                IOMapping(
                    upstream_operator=Process,
                    upstream_output_channel="processed-data",
                    input_channel="data-for-upload",
                )
            ],
        )

    GetInput >> Process >> Upload


The repository contains an `example processing-pipeline <https://codebase.helmholtz.cloud/kaapana/kaapana/-/tree/d9af4682030c7f21286e348f0fb917c059557ea9/data-processing/processing-pipelines/task-api>`_ containing a processing-container and a DAG with two tasks.


Passing user input to a task-run
=========================================

Many Dags require input from a user, e.g. input datasets or selection for organ segmentations.
This user input has to be passed as environment variables to a dedicated TaskRun in the DagRun.
The user input as environment variables can be configured in the :code:`conf` object in the body of the initial request to the Airflow Rest API that starts a DagRun.
The :code:`KaapanaTaskOperator` receives this :code:`conf` object and overrides the environment variables accordingly.

The :code:`conf` object must look like this

.. code-block:: bash
    :caption: The conf object in the request body

    {
      "task_form": {
        "{TASK_ID_1}": {
          "{VAR_NAME_1}": "{VAR_VALUE_1}"
        },
        "{TASK_ID_2}": {
          "{VAR_NAME_2}": "{VAR_VALUE_2}"
        }
      }
    }


An example request to trigger a DagRun with custom environment variables would look like this:

.. code-block:: bash
    :caption: Example curl command to trigger a DagRun with user input to a task.

    curl -X 'POST' \
    'https://my-kaapana-domain.de/flow/api/v1/dags/my-dag/dagRuns' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "dag_run_id": "run-dag-with-user-input-23jdk",
    "conf": {
        "task_form": {
            "get-data": {
                "DATASET": "study-123" 
                }
            }
        }
    }'


This request will start a DagRun for :code:`my-dag`.
In the TaskRun of the :code:`get-data` task the environment variable :code:`DATASET` will be set to :code:`study-123`.


.. note::

  The :code:`dag_run_id` must be unique for each DagRun.


Order of precedence for environment variables
------------------------------------------------


When environment variables are defined in multiple places, the following order determines which value takes effect (highest priority first):

1. Variables set in the :code:`conf` object in the DagRun trigger request.
2. Variables set in the :code:`env` parameter set for the :code:`KaapanaTaskOperator`.
3. Default variables set in the task template in the :code:`processing-container.json` file in the container image.

In other words, values from the workflow request override those from the operator, which in turn override defaults from the container definition.



Container images from an external registry
===========================================

If your processing-container image is hosted in an external registry, you can configure authentication by setting the parameters listed below.  
When provided, Kaapana automatically creates a dedicated registry secret that allows the task to pull the image securely during execution.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Parameter
     - Description
   * - :code:`registryUrl`
     - URL of the external container registry (e.g. :code:`https://registry.example.com`)
   * - :code:`registryUsername`
     - Username used to authenticate with the registry
   * - :code:`registryPassword`
     - Password or access token used for authentication


Features not yet supported by the KaapanaTaskOperator
======================================================

Some features, that are supported in the KaapanaBaseOperator are not supported in the KaapanaTaskOperator:

* The :code:`conf` object is not mounted into the container.
* Starting a code-server as development server.
* ui_forms: data_form, workflow_form