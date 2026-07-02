.. _experimental:

Experimental
^^^^^^^^^^^^

.. warning::

   As of v0.7.0, the services explained in this section are still **experimental and not yet used as the default**.
   These services are part of an ongoing migration and are **not** the supported way of working with the platform yet.
   Their APIs, schemas and behaviour may change until they are stabilized. 
   For users and developers who want to use Kaapana in production, please keep following the supported documentation in the other sections.

Kaapana is transitioning from a set of monolithic, :code:`kaapana-backend` centric components towards a collection of targeted and single-purpose **APIs**. 
The goal is to make the platform more scalable, modular, decentralized, easier to maintain.
During this transition, both the *legacy* (supported) and the *new* (experimental) implementations can be found in the platform. 
This page gives an overview of how these new services function as main pillars of the platform's architecture, the sub-pages document each new service in detail.

Old vs. new services
********************

.. list-table::
   :header-rows: 1
   :widths: 22 38 40

   * - Domain
     - New (experimental)
     - Old (supported, still the default)
   * - Workflows
     - :ref:`workflow-api <experimental_workflow_api>`: engine-agnostic REST
       API for workflows, revisions and runs
     - ``kaapana-backend`` workflow endpoints + Airflow
   * - Tasks / processing containers
     - :ref:`task-api <experimental_task_api>`: a contract and library for
       running processing containers (already usable today)
     - DAG operators based on ``KaapanaBaseOperator``
   * - Data
     - :ref:`data-api <experimental_data_api>`: ``data_api`` client SDK for the
       Data & Storage (entities, metadata, artifacts)
     - ``kaapana-backend`` data endpoints
   * - Extensions
     - :ref:`extension-manager <experimental_extension_manager>`: OCI-based
       extensions (service, UI and ``extensionctl`` toolchain)
     - ``kube-helm`` backend + Extensions page


.. toctree::
    :maxdepth: 1

    experimental/workflow_api
    experimental/task_api
    experimental/data_api
    experimental/extension_manager
