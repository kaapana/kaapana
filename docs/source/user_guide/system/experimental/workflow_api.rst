.. _experimental_workflow_api:

Workflow API
^^^^^^^^^^^^

.. warning::

   Experimental and not yet the default. 
   The supported way of running workflows remains the ``kaapana-backend``, together with Airflow.

A unified REST API for managing workflows and their runs across different workflow engines (Airflow, Argo, Kubeflow, …).

- **Workflow**: definition of tasks and dependencies.
- **WorkflowRun**: single execution of a workflow.
- **Task / TaskRun**: individual steps and their executions.

The API handles posting workflows, configuring and triggering runs, retrieving run/task state and logs.
The communication with a workflow engine is handled by a pluggable **engine adapter** (currently only an Airflow adapter is implemented).

More details
************

- Architecture, data model and design decisions: ``services/base/workflow-api/docker/files/README.md``
- Live request/response schemas: the service's OpenAPI/Swagger UI