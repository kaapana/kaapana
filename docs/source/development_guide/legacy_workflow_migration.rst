.. _legacy_workflow_migration:

==========================
Migrating Legacy Workflows
==========================

Migrating from KaapanaBaseOperator
##################################

This section explains how to migrate a processing-container that was previously used with an Airflow operator inheriting from :code:`KaapanaBaseOperator` to one that works with the new :code:`KaapanaTaskOperator`.


The :code:`KaapanaBaseOperator` imposed several *implicit conventions* that affected how processing-containers interacted with the workflow environment.  
In contrast, the :code:`KaapanaTaskOperator` makes all expectations explicit through the Task API and the :code:`processing-container.json` file.

The following table summarizes the main differences:

.. list-table::
   :header-rows: 1
   :widths: 30 30

   * - :code:`KaapanaBaseOperator`
     - :code:`KaapanaTaskOperator`
   * - All workflow directories are mounted into the container.
     - Only declared input and output channels are mounted.
   * - File paths must be constructed from environment variables.
     - File paths are always relative to the :code:`mounted_path` of the respective channel.
   * - Environment variables for file path construction are set automatically.
     - No environment variables are set automatically.
   * - Variables in :code:`conf` are shared between all tasks in a workflow run.
     - Variables in :code:`conf` are specific to each task run.

The most significant difference is **how data is mounted into containers**.

Legacy Data Mounting (KaapanaBaseOperator)
===========================================

When using the :code:`KaapanaBaseOperator`, each container received a generic directory structure that included workflow-level paths and environment variables such as :code:`WORKFLOW_DIR`, :code:`BATCH_NAME`, :code:`OPERATOR_IN_DIR`, and :code:`OPERATOR_OUT_DIR`.

For example, given the following DAG:

.. code-block:: python

    dag = DAG(dag_id="my_dag")

    get_input = GetInputOperator(dag=dag)
    my_algorithm = MyAlgorithmOperator(dag=dag, input_operator=get_input)

    get_input >> my_algorithm

Kaapana automatically mounted the following directory structure in the container of :code:`my_algorithm`:

.. code-block:: bash

    └── ${WORKFLOW_DIR}
        ├── ${BATCH_NAME}
        │   ├── item-1
        │   │   └── ${OPERATOR_IN_DIR}/input
        │   └── item-2
        │       └── ${OPERATOR_IN_DIR}/input
        └── conf/conf.json

After processing, the resulting structure typically looked like this:

.. code-block:: bash

    └── ${WORKFLOW_DIR}
        ├── ${BATCH_NAME}
        │   ├── item-1
        │   │   ├── ${OPERATOR_IN_DIR}/input
        │   │   └── ${OPERATOR_OUT_DIR}/result
        │   └── item-2
        │       ├── ${OPERATOR_IN_DIR}/input
        │       └── ${OPERATOR_OUT_DIR}/result
        └── conf/conf.json


Migrated Data Mounting (KaapanaTaskOperator)
===============================================

When migrating to the :code:`KaapanaTaskOperator`, data mounts are **defined explicitly** in the :code:`processing-container.json` file and linked between tasks using :code:`IOMapping` objects.

For example, the previous DAG can be migrated as follows:

.. code-block:: python
    :caption: my_dag.py

    with DAG("my_dag", default_args=args) as dag:
        get_input = KaapanaTaskOperator(
            task_id="get_input",
            image=f"{DEFAULT_REGISTRY}/get-input:{KAAPANA_BUILD_VERSION}",
            taskTemplate="dicom",
        )

        my_algorithm = KaapanaTaskOperator(
            task_id="my_algorithm",
            image=f"{DEFAULT_REGISTRY}/my-algorithm:{KAAPANA_BUILD_VERSION}",
            taskTemplate="my_algorithm",
            iochannel_maps=[
                IOMapping(
                    upstream_operator=get_input,
                    upstream_output_channel="downloads",
                    input_channel="inputs",
                )
            ],
        )

    get_input >> my_algorithm

.. note::

  The :code:`upstream_output_channel` of the :code:`get_input` task is :code:`downloads`.
  This is explicitly declared in the corresponding task template in the :code:`processing-container.json` file of the :code:`get-input` image.


Following the :ref:`data structure convention <data_structure_convention>`, the directory structure inside the container for :code:`my_algorithm` now looks similar to this:

.. code-block:: bash

    └── input-mount-path
    │   ├── item-1/input
    │   └── item-2/input
    └── output-mount-path
        ├── item-1/result
        └── item-2/result

This makes data flow between tasks more explicit and modular, removing hidden assumptions about directory layouts or shared environment variables.