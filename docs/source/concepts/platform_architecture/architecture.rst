.. _concepts_architecture:

Backend Architecture
################################################

Kaapana is a cloud-native platform: every service and processing step runs as a Docker container on Kubernetes, packaged and installed as Helm charts (see :ref:`concepts_extensions_system`), and able to scale from one machine to a multi-node cluster (see :ref:`concepts_multi_node_architecture`). Authentication is standardized on OAuth2 / OpenID Connect against Keycloak as the identity provider -- see :ref:`concepts_authorization_flow` for the full request chain.

The rest of this page is about a narrower, second axis of that architecture: the custom, in-house services that make up the backend -- what each one owns, what it's built with, and which are legacy pieces being replaced. This is the canonical description of these services; other pages link back here instead of repeating it.

Until Kaapana 0.5.x, almost the entire backend lived in a single service, :term:`kaapana-backend`.
It managed workflow jobs (tightly coupled to Apache Airflow), DICOM/dataset metadata in OpenSearch, platform settings, file uploads, and federated instance-to-instance communication, all in one FastAPI application with one database schema.
That coupling made it hard to evolve one concern (say, supporting a workflow engine other than Airflow) without risking every other concern in the same service.

Starting with **Kaapana 0.6.0**, new, narrowly scoped services were introduced *alongside* :term:`kaapana-backend` to take over specific responsibilities, one concern at a time.
Each new service follows the same pattern: a FastAPI backend, its own PostgreSQL database, and a dedicated Vue 3 frontend.
:term:`kaapana-backend` keeps running the concerns that have not moved to a new service yet.

Kube-Helm
================================================

**Kube-Helm** is the other service that predates the Kaapana 0.6.0 decomposition alongside :term:`kaapana-backend`: a FastAPI service that currently does two unrelated jobs at once.

* **Distribution** -- it receives uploaded Helm charts and container images (the file-upload endpoints behind the *Local build and manual upload* and *Air-gapped transfer* paths in :ref:`concepts_workflow_distribution`) and runs ``helm install``/``helm delete`` for them.
* **Running applications** -- it tracks active applications (which ones are running, in which project) and completes them when their workflow signals they're done.

Both jobs are being split out into their own focused services, following the same pattern as the rest of this page: distribution into the OCI-based **Extension Manager** (below), and application/workflow execution into **Workflow API**. Plain Helm install/delete -- for whatever Extension Manager doesn't cover yet -- is planned to move into its own **Helm API** next.

Task API
================================================

Historically, every :term:`processing-container` was wired into a workflow through Python code: a :term:`local-operator` or a ``KaapanaBaseOperator`` subclass in an Airflow DAG.
The **Task API** -- ``task_api``, a Python library rather than a deployed service -- turns that wiring into a declared contract instead: a processing-container ships a ``processing-container.json`` file describing its task templates, inputs/outputs and command, and a small runner library (usable with Kubernetes or plain Docker) executes it based on that declaration alone.

A task template can declare several named input and output channels, and ``KaapanaTaskOperator``'s ``iochannel_maps`` wires an upstream task's output channel to a downstream task's input channel. Composing processing-containers into a multi-step, multi-modal workflow becomes a declared mapping between channel names, rather than custom Python code moving files between containers.

See :ref:`processing_container_dev_guide` for the full schema and how to build a compliant container.

In practice, ``KaapanaBaseOperator`` now uses the Task API's Kubernetes runner internally to start its pods, so every existing DAG already benefits from it indirectly.
Kaapana is moving toward writing new DAGs directly against the Task API through ``KaapanaTaskOperator``: the ``register-dicoms`` and ``test-task-operator`` example workflows already use it this way, with more DAGs adopting the same pattern going forward.

Workflow API
=================================================

:term:`kaapana-backend` originally exposed workflow jobs as a thin wrapper around Airflow's own concepts: a job *was* an Airflow DAG-run, addressed by DAG id.
The **Workflow API** -- ``workflow-api``, FastAPI + PostgreSQL, paired with the ``workflow-ui`` Vue 3 frontend -- replaces that with its own persistent model:

* **Workflow** -- a named, versioned definition. Each edit creates a new **WorkflowRevision**; earlier revisions can be restored.
* **WorkflowRun** -- one execution of a specific revision, with an overall lifecycle status.
* **Task** / **TaskRun** -- the steps of a workflow and their per-run execution status and logs.

Everything that actually talks to the execution engine is behind a ``WorkflowEngineAdapter`` interface.
An Airflow adapter implements this interface by driving Airflow's REST API and mapping Airflow DAG/task states onto the WorkflowRun/TaskRun model above; a dummy adapter exists for testing the API without Airflow at all.
Because the engine is hidden behind this interface, a future non-Airflow engine could be added without changing the Workflow/WorkflowRun model or its API.

.. _concepts_architecture_data_api:

Data API
=========================================

:term:`kaapana-backend`'s dataset endpoints are built directly on top of the DICOM metadata that Kaapana indexes in OpenSearch -- they answer questions like *"which series match this filter"*.
The **Data API** -- ``data-api``, FastAPI + PostgreSQL, paired with the ``data-ui`` Vue 3 frontend -- is a separate, more general interface for **data entities**: arbitrary records identified by a UUID, with

* backend-agnostic **storage coordinates** (a PACS, an S3 bucket, a filesystem path, or a plain URL) pointing to where the raw data actually lives,
* schema-validated **metadata entries**, stored in the Data API's own database, and
* binary **artifacts** (e.g. a thumbnail or a generated report) attached to a metadata entry.

The Data API itself does not store the raw data it describes -- it stores metadata and a pointer to wherever the data lives.
A workflow's non-DICOM output -- a radiomics feature table, a validation report -- gets the same UUID, storage-coordinate and schema-validation treatment as any other entity, instead of each workflow inventing its own file layout and metadata convention.
It currently coexists with the DICOM/OpenSearch metadata search that :term:`kaapana-backend` provides.
Because any record -- a model, a training run, a dataset -- is just another entity, and an entity can reference a parent entity, the Data API can also represent relationships such as data provenance or a fine-tuned model's lineage back to its base model or training data.
There is no dedicated support for ML models specifically yet -- no model registry, no versioning beyond the generic entity/parent mechanism above. The idea is to build that on top of the same entity model rather than a separate system; the concrete design is TBD.

Extension Manager
================================================

The **Extension Manager** -- ``extension-manager-service``, FastAPI + PostgreSQL, paired with the ``extension-manager-ui`` Vue 3 frontend -- is a service responsible for distributing software -- tasks, workflows and applications -- pulled from an OCI registry. Currently, it lives alongside the existing Helm-chart upload path (still handled by **Kube-Helm**, above) and supports an installer for the ``workflow-v1`` content type; installers for tasks and applications are anticipated. See :ref:`concepts_extensions_system` for the manifest format and installation lifecycle.

Access Information Interface (AII)
================================================

The **Access Information Interface** -- ``access-information-interface``, FastAPI + PostgreSQL, paired with the ``project-management-ui`` Vue 3 frontend -- describes the roles and rights users hold within projects -- it is the service behind the rights/roles/projects model described in :ref:`Access Control<access_control_root>`. Unlike the services above, it isn't part of the :term:`kaapana-backend` decomposition: it addresses project-level multi-tenancy, a separate concern from splitting up the legacy monolith.

.. _concepts_architecture_dicom_web_filter:

DICOM Web Filter
================================================

The **DICOM Web Filter** -- ``dicom-web-filter``, FastAPI + PostgreSQL -- sits in front of DICOMweb (STOW-RS) ingestion (see the :ref:`service-process-incoming-dcm<service_process_incoming_dcm>` DAG for what happens once a series is received) and adds data/project separation on top of the internal PACS. It enables connecting to any DICOMweb-compliant storage, not just the local dcm4chee PACS, and gives fine-grained control over which user or project can access a given DICOM series.

Future Direction
================

Kaapana is moving concerns out of :term:`kaapana-backend` and **Kube-Helm** into focused services one at a time. Distribution, Data Management, and Workflow Execution are already worked on and partially completed. Federation is expected to follow the same path into its own service, making it FL framework-agnostic.
