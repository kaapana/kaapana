.. _concepts_viewing_and_frontend:

Viewing and Frontend
######################

Connecting a viewer or application to Kaapana's data is mostly a matter of configuration, not code -- the viewer or app is currently wired to specific storage endpoints (Minio, dicom-web-filter).

Connecting to DICOM Data
============================

**OHIF** (``ohif-viewer``, under the Store) and the **Slim Viewer** (``slim-viewer``, an application) both resolve their DICOMweb endpoint at runtime from the page's own hostname: ``https://<hostname>/dicom-web-filter``.
Neither viewer has a PACS address baked in -- they speak DICOMweb against whatever ``/dicom-web-filter`` resolves to on the platform that served them.
Because of this, if the platform's :ref:`DICOM Web Filter<concepts_external_pacs>` is pointed at an external DICOMweb store instead of the internal PACS, both viewers follow transparently; there is nothing viewer-specific to reconfigure.

Connecting to MinIO
=======================

Applications that need non-DICOM data, such as **MITK Workbench**, do not talk to MinIO's S3 API directly either. A ``minio-mirror`` sidecar container handles the connection: it is given the MinIO service address, project credentials, and a bucket path (``MINIO_SERVICE``, ``MINIO_USER``, ``MINIO_PASSWORD``, ``MINIO_PATH``), and mirrors that bucket path to and from a local directory the application reads and writes as if it were a plain filesystem.

Future Direction
====================

The plan is to route this through the :ref:`Data API<concepts_architecture_data_api>` instead: a filesystem-style view over arbitrary data, with DICOM access still going through the DICOM Web Filter.
