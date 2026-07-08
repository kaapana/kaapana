.. _use_cases:

Use Cases
#######################

Kaapana ships as a platform together with a growing set of workflow and application
extensions supporting medical image analysis use cases.
This page is a snapshot of what is available out of the box; the version-specific list
for your own deployment is always the :ref:`Extensions page<extensions>`.


Data Pipeline
======================

The sections below follow that path through a typical Kaapana deployment: data comes in,
gets reviewed and annotated, is processed by a workflow, and the results are stored,
viewed and optionally shared across sites.

Data Upload
-------------------

Data reaches Kaapana as a DICOM series sent to the internal PACS, or as an arbitrary
file, registered through the Data API.
Data is anonymized, and DICOM header and acquisition parameters are extracted through the automatic pipeline
into searchable metadata. Data can be transformed and converted on the fly, e.g. whole-slide microscopy images can be converted to DICOM.

See the :ref:`Data Upload guide<data_upload>` for the DICOM and browser-based upload
paths.

Organizing Datasets
-----------------------

Once data has landed, it gets grouped, searched and tagged into datasets that workflows
run against and that can be used for Federated Learning across multiple Kaapana instances.
See the :ref:`Datasets guide<datasets>` for how the gallery, search and tagging work.

Reviewing and Annotating
----------------------------

A series can be inspected directly in the browser, or opened in a desktop-style viewer
for volume or whole-slide annotation -- **OHIF** (see :ref:`store`), **MITK Workbench**,
**3D Slicer Workbench** and the **SLIM Viewer** all connect back to the same underlying
data.

Running a Workflow
----------------------

From there, a dataset can be sent through a processing workflow: **TotalSegmentator v2**
and **nnU-Net** for organ and structure segmentation, **Body and Organ Analysis (BOA)**
for CT-based organ analysis built on top of TotalSegmentator, **Radiomics** for feature
extraction from segmentation objects, or a **Classification workflow** to train or run
inference for binary/multiclass/multilabel 2D/3D models.
**Body part regression** predicts where along the body axis a CT image was taken, and
**Advanced metadata collection** gathers image intensity and segmentation statistics
across a dataset. 
See :ref:`Workflow Execution<workflow_execution>` for how a workflow is configured and
started, and :ref:`Workflow List<workflow_list>` for tracking it while it runs.

Automation and Custom Development
-------------------------------------

Any of the above can be chained or triggered automatically and new workflows can be 
developed directly on the platform using **Extension Development Kit** -- in-browser
environments for writing DAGs, operators and extensions.
See :ref:`extensions` and :ref:`concepts_extensions_system` for how these are packaged
and installed.

Interactive Environments
-------------------------

For exploratory work rather than a fixed pipeline, **JupyterLab** gives a notebook
environment with direct access to Kaapana's APIs (see :ref:`concepts_programmatic_access`),
and **TensorBoard** visualizes training runs as they happen.
Both are :ref:`Active Applications<active_applications>` that can be launched by a workflow, 
that waits for an interactive step to be finished -- see :ref:`concepts_interactive_workflows`.

Result Storage
----------------------------

A workflow's output is not limited to one format: segmentation results are written back
as DICOM (``.dcm``) objects, radiomics features and metadata as ``.xlsx`` or ``.csv``,
and reports or documentation as ``.docx``/``.pdf``, all stored through the same Data API
used for input.
See :ref:`store` and :ref:`concepts_file_types` for how DICOM and non-DICOM
results are kept separately in the internal PACS and MinIO or external storage.

Viewing Results
-----------------------

Those results can then be opened again in the same viewers used earlier in the pipeline
-- **OHIF** or **MITK/3D Slicer** for DICOM segmentations, **SLIM Viewer** for
whole-slide results -- and documents or reports can be opened and edited directly in
**Collabora**.
See :ref:`store` and :ref:`concepts_viewing_and_frontend` for how these viewers connect
back to the platform.

Federated Execution
---------------------------

Finally, most of these workflows -- **nnU-Net**, **Radiomics**, **Advanced metadata
collection** -- have a federated variant that runs the same computation across multiple
Kaapana instances, keeping training or feature extraction on local data and sending
only model weights or aggregated results to an orchestrator.
See :ref:`concepts_federated_learning`.

Platform Properties
======================

None of the above depends on a single machine or a fixed set of workflows.

* **Stability** -- workflow execution, generic data storage, and extension
  distribution each run as their own service with their own database, so a bug or
  outage in one does not take down or require re-testing the others.
  See :ref:`concepts_architecture`.
* **Scaling** -- a deployment can grow from a single machine to a multi-node cluster,
  routing GPU-heavy workflows to dedicated nodes, sharing a single GPU across several
  concurrent tasks instead of reserving one per job, and exposing cluster and task
  health through Prometheus, Grafana and Loki. See :ref:`concepts_multi_node_architecture`,
  :ref:`concepts_gpu_sharing` and :ref:`concepts_monitoring_and_resources`.
* **Extendability** -- new workflows and applications are packaged as ordinary Helm
  charts and can be built, tested and distributed without forking the platform, whether
  that means writing a new DAG on the platform itself or shipping a standalone
  extension to other Kaapana instances. Workflow execution itself is engine-agnostic by
  design: the Workflow API talks to Airflow through a standardized adapter interface,
  so any workflow engine can be plugged in by implementing an adapter, without changing
  the workflow model itself. See :ref:`concepts_extensions_system`, :ref:`concepts_workflow_distribution`
  and :ref:`concepts_architecture`.
* **Access control** -- every study, team or dataset gets its own access-controlled
  project -- its own storage bucket, its own DAG permissions, its own users -- so
  multiple studies or teams can run on the same platform without standing up a separate
  Kaapana instance per study. See :ref:`Access Control<access_control_root>`. User
  identity itself does not have to live in Kaapana either: :ref:`Keycloak<keycloak>` can
  federate against an institution's own Active Directory over LDAP or Kerberos, so users
  log in with their existing directory credentials.
