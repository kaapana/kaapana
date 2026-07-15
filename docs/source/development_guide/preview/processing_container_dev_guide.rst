.. _processing_container_dev_guide:

==================================
Processing-Container Development
==================================

A :term:`processing-container` refers to a container image designed to perform data processing tasks.  
These containers are typically executed as tasks in a workflow, e.g. during data pre-processing, model training, or post-processing steps.

To make the requirements that Kaapana imposes on processing-containers **explicit and standardized**, we developed the **Task API**.
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
It must conform to the `processing-container JSON schema <https://codebase.helmholtz.cloud/kaapana/kaapana/-/raw/develop/lib/task_api/task_api/processing_container/ProcessingContainer.schema.json?ref_type=heads>`_.

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


.. _TaskTemplate:

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

.. _TaskTemplateEnv:

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


.. _IOMount:

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


.. _ScaleRule:

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


.. _Resources:

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

The CLI is included in the `task-api` package, which can be installed directly from the Kaapana repository using `pip <https://pypi.org/project/pip/>`_:

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
The file has to comply to the `task JSON Schema <https://codebase.helmholtz.cloud/kaapana/kaapana/-/raw/develop/lib/task_api/task_api/processing_container/Task.schema.json?ref_type=heads>`.

Required fields in the :file:`task.json` file:

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Human-readable name for this task execution.
   * - ``api_version``
     - integer
     - API version of the task specification (current version is 1).
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
     - array of :code:`BaseEnv`
     - Environment variables to override template defaults. :code:`BaseEnv` has attributes :code:`name` and :code:`value`.
   * - ``command`` *(optional)*
     - array of strings
     - Overrides the default container command or task template command.
   * - ``resources`` *(optional)*
     - :ref:`Resources`
     - Resource requests and limits (CPU, memory, GPU) for this task.
   * - ``config`` *(optional)*
     - :code:`DockerConfig` or :code:`K8sConfig`
     - Container runtime configuration (e.g., Docker labels, Kubernetes namespace), see `here <https://codebase.helmholtz.cloud/kaapana/kaapana/-/raw/develop/lib/task_api/task_api/processing_container/task_models.py?ref_type=heads>_`

.. _IOVolume:

Inputs and Outputs: IOVolume
----------------------------

Each input or output channel is represented by an :code:`IOVolume` object, which defines the channel name, the local path to mount, and optional scaling rules.

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
      "api_version": 1,
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

Output channel
===============

We assume, that any channel contains results for 1 to N items.
Then we expect the output channel to have the following structure

.. code-block:: bash
    :caption: Convention for output channel structure
    
    └── output-mount-path
        ├── item-1-identifier
        │   └── result
        ├── item-2-identifier
        │   └── result
        ├── ...
        └── item-N-identifier
            └── result

Item identifiers in input and output channels
==============================================

Output items are expected to have the same identifier as the input item that was used to create it.

.. code-block:: bash
    :caption: Convention for identifiers
    
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

Item identifiers when combining multiple inputs items into one output item
============================================================================

Output items, that are created by processing multiple input items from the same channel, are expected to have a new unique identifier.

.. code-block:: bash
    :caption: Convention for combined output items
    
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

Best practice for developing a processing-container
####################################################

When developing a processing-container, the goal is to make your component **modular, reusable, and easy to integrate into workflows**.  
Follow these guidelines to align with Kaapana’s conventions:

* **Provide a command-line interface (CLI)**
  Structure your application so that it can be executed as a standalone command-line tool.  
  This allows it to be easily called from scripts or workflow tasks.

* **Design clear input and output parameters**
  The command-line interface should accept one or more input channels or data items as parameters (e.g., file paths or directories).  
  This ensures that your tool can be connected seamlessly to workflow I/O definitions.

* **Create a wrapper script to handle batch processing**
  Write a small wrapper script (e.g. a Bash script) that loops over all items in the input channel and calls your command-line tool for each item.  
  The wrapper should also write each result into the corresponding output channel.

* **Use the wrapper script as the container’s entrypoint command**
  In your task template, specify the wrapper script as the container’s :code:`command`.  
  This makes your container self-contained and automatically executable by the workflow engine.

* **Include all essential components for reproducibility**
  Provide the following files in your container definition:
  
  - The command-line tool (or its dependencies)
  - The wrapper script
  - A Dockerfile describing how to build the image
  - A task template inside :code:`processing-container.json` defining inputs, outputs, and the command

These steps together ensure that your processing-container is **consistent, testable, and easy to integrate** into Kaapana workflows.


Example processing-container
=============================

The example processing-container should include a task template for converting dicom series to nrrd file by utilizing MITK.
We use the :code:`base-mitk` image that build during building Kaapana.
MITK comes with :code:`MitkFileConverter` tool that supports the conversion from dicom to nrrd.
The entrypoint for the corresponding command line tool in the :code:`base-mitk` image is at :code:`/kaapana/app/apps/MitkFileConverter.sh`.

.. code-block:: bash
    :caption: Usage of the MitkFileConverter in the base-mitk image

    /kaapana/app/apps/MitkFileConverter.sh -i <input dicom directory> -o <output path to the .nrrd file>

The MitkFileConverter already supports the best practice: 
* We can specify the path to an input directory with the :code:`.dcm` files.
* We can specify the path to the output file.



Example wrapper script in bash
---------------------------------

The following bash script iterates over all items in in :code:`/home/kaapana/dicom` and creates output items in :code:`/home/kaapana/nrrd`.
It uses the same identifier from the input items for the respective output items.

.. code-block:: bash
    :caption: convert.sh

    #! /bin/bash
    set -eu -o pipefail

    ROOT_INPUT_DICOM_DIR="/home/kaapana/dicom"
    ROOT_OUTPUT_NRRD_DIR="/home/kaapana/nrrd"

    for INPUT_DICOM_DIR in $( find ${ROOT_INPUT_DICOM_DIR} -mindepth 1 -maxdepth 1 -type d); do
        IDENTIFIER=$( basename ${INPUT_DICOM_DIR} )
        mkdir -p ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}
        /kaapana/app/apps/MitkFileConverter.sh -i ${INPUT_DICOM_DIR} -o ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}/${IDENTIFIER}.nrrd
    done


Example task template
-----------------------


The :code:`processing-container.json` that contains the task-template for dicom to nrrd conversion could look like this:

.. code-block:: bash
  :caption: processing-container.json

    {
      "name": "mitk-tools",
      "description": "Processing container for tasks using MITK apps",
      "templates": 
      [
          {
              "identifier": "dicom-to-nrrd",
              "description": "Convert dicom series to nrrd files",
              "env": [
              ],
              "inputs": [
                  {
                      "name": "dicom",
                      "mounted_path": "/home/kaapana/dicom",
                  }
              ],
              "outputs": [
                  {
                      "name": "nrrd",
                      "mounted_path": "/home/kaapana/nrrd"
                  }
              ],
              "command": ["/bin/bash", "/home/kaapana/convert.sh"]
          }
      ]
    }

* The :code:`mounted_path` of the :code:`dicom` input channel corresponds to the :code:`ROOT_INPUT_DICOM_DIR` in :code:`convert.sh`.
* The :code:`mounted_path` of the :code:`nrrd` output channel corresponds to the :code:`ROOT_OUTPUT_NRRD_DIR` in :code:`convert.sh`.
* The :code:`command` declares to execute the wrapper script at :code:`/home/kaapana/convert.sh`.

Example Dockerfile
-------------------

The Dockerfile for the processing-container image could look like this

.. code-block:: bash
  :caption: Dockerfile

  FROM local-only/base-mitk:latest
  LABEL IMAGE="mitk-tools"
  LABEL BUILD_IGNORE="False"

  COPY processing-container.json /
  WORKDIR /home/kaapana
  COPY files/convert.sh /home/kaapana/


* The base image :code:`local-only/base-mitk:latest` contains the MitkFileCoverter
* The :code:`LABEL` fields are used by the build-script of Kaapana.
* The file :code:`processing-container.json` is copied to the root directory of the container image.
* The wrapper script at :code:`files/convert.sh` is copied to the locations, where it is expected by the task template.