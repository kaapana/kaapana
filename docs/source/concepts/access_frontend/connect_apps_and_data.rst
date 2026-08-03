.. _concepts_connect_apps_and_data:

Connecting Viewers and Applications to Data
###############################################

Connecting a viewer or application to Kaapana's data is mostly a matter of configuration, not code -- the viewer or app is currently wired to specific storage endpoints (Minio, dicom-web-filter).

Connecting to DICOM Data
============================

**OHIF** (``ohif-viewer``, under the Store) and the **Slim Viewer** (``slim-viewer``, an application) both resolve their DICOMweb endpoint at runtime from the page's own hostname: ``https://<hostname>/dicom-web-filter``.
Neither viewer has a PACS address baked in -- they speak DICOMweb against whatever ``/dicom-web-filter`` resolves to on the platform that served them.
Because of this, if the platform's :ref:`DICOM Web Filter<concepts_external_pacs>` is pointed at an external DICOMweb store instead of the internal PACS, both viewers follow transparently; there is nothing viewer-specific to reconfigure.

The same endpoint handles annotations going back in. Both viewers are configured with STOW-RS write access (OHIF's ``stowRoot``, Slim's ``write: true`` server flag) against the same ``/dicom-web-filter`` URL used for reading, so an annotation created in the viewer -- a Slim Viewer measurement or an OHIF structured report -- is saved as a DICOM SR object back through the same route the viewer reads from. That write is forwarded to CTP the same way as any other incoming DICOM (see :ref:`concepts_file_types`), so a saved annotation runs through the full ingestion pipeline -- validated and thumbnailed like any other series -- rather than being written directly into the PACS.

Connecting to MinIO
=======================

Applications that need non-DICOM data connect to MinIO one of two ways, depending on what the application itself expects.
**Collabora** talks to MinIO's S3 API directly, using per-user, token-scoped credentials obtained via ``AssumeRoleWithWebIdentity``.
Applications that instead expect a plain filesystem, such as **MITK Workbench**, get one via a ``s3-mirror`` sidecar container: it is given the MinIO service address, project credentials, and a bucket path (``S3_SERVICE``, ``S3_USER``, ``S3_PASSWORD``, ``S3_PATH``), and mirrors that bucket path to and from a local directory the application reads and writes as an ordinary filesystem.

Future Direction
====================

The plan is to route this through the :ref:`Data API<concepts_architecture_data_api>` instead: a filesystem-style view over arbitrary data, with DICOM access still going through the DICOM Web Filter.
