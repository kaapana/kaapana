.. _concepts:

Concepts Overview
###################

The :ref:`User Guide<user_guide>` and :ref:`Extension Development Guide<develop_guide>` describe **how** to use and extend Kaapana.
This section instead explains **why** some of its core subsystems are built the way they are: the reasoning behind a design, how the pieces fit together, and what is still evolving.

Platform Architecture
========================

* :ref:`concepts_architecture` -- how the backend moved from one monolithic service to several narrowly scoped ones.
* :ref:`concepts_multi_node_architecture` -- running Airflow workers, GPU workflows, PACS and MinIO across more than one machine.
* :ref:`concepts_gpu_sharing` -- letting several tasks share one physical GPU instead of reserving a whole device per task.
* :ref:`concepts_monitoring_and_resources` -- how CPU, RAM and GPU are scheduled, and how cluster/task health is exposed.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Platform Architecture

   concepts/platform_architecture/architecture
   concepts/platform_architecture/multi_node_architecture
   concepts/platform_architecture/gpu_sharing
   concepts/platform_architecture/monitoring_and_resources

Data & Storage
================

* :ref:`concepts_cloud_storage` -- where the data is actually stored on single-node vs. multi-node deployments.
* :ref:`concepts_external_pacs` -- pointing the platform's DICOMweb ingestion/query path at an external PACS.
* :ref:`concepts_workflow_storage` -- how a workflow's processing pods get and hand off their data.
* :ref:`concepts_file_types` -- what file types are supported, through which mechanism, and what else is possible.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Data & Storage

   concepts/data_storage/cloud_storage
   concepts/data_storage/external_pacs
   concepts/data_storage/workflow_storage
   concepts/data_storage/file_types

Workflows & Extensions
========================

* :ref:`concepts_workflow_distribution` -- how an extension is packaged and distributed and how it gets into Kaapana.
* :ref:`concepts_interactive_workflows` -- how a workflow spawns an application and waits on it for confirmations, annotation, or other human-in-the-loop steps.
* :ref:`concepts_federated_learning` -- running a computation across multiple Kaapana instances without moving raw patient data.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Workflows & Extensions

   concepts/workflows_extensions/distributing_extensions
   concepts/workflows_extensions/interactive_workflows
   concepts/workflows_extensions/federated_learning

Access & Frontend
====================

* :ref:`Access Control<access_control_root>` -- controlling access to data, workflows and other resources.
* :ref:`concepts_authorization_flow` -- how a request is authenticated and authorized on its way to a backend service.
* :ref:`concepts_programmatic_access` -- calling Kaapana's workflow APIs from a script or notebook.
* :ref:`concepts_connect_apps_and_data` -- why connecting a viewer or application is a matter of configuration, not code.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Access & Frontend

   concepts/access_frontend/access_control_root
   concepts/access_frontend/authorization_flow
   concepts/access_frontend/programmatic_access
   concepts/access_frontend/connect_apps_and_data
