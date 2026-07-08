.. _concepts_file_types:

File Types
################################

What file types Kaapana handles, and through which mechanism, differs by type.

DICOM
========

DICOM is the primary supported type. It reaches the internal PACS via classic DIMSE C-STORE or DICOMweb STOW-RS (through the :ref:`DICOM Web Filter<concepts_external_pacs>`). Both paths converge on the :ref:`Clinical Trial Processor (CTP)<store>`, which receives the DICOM directly (DIMSE) or via the DICOM Web Filter's forwarded STOW-RS traffic, before the :ref:`service-process-incoming-dcm<service_process_incoming_dcm>` ingestion DAG picks it up, validates it, and creates a thumbnail. Other automatic pipelines can be autotriggered here like pseudoanonymization, whole-slide microscopy conversion, or radiomics feature extraction. The ingestion DAG then hands the DICOM off to the PACS for storage and indexing.

Arbitrary Non-DICOM Files
============================

Arbitrary non-DICOM files are currently uploaded through the web interface's :ref:`Data Upload page<data_upload>` and land in **MinIO**, where they can be browsed and managed as ordinary bucket objects. This is the current path for anything that is not DICOM.

Data API (Work in Progress)
===============================

The :ref:`Data API<concepts_architecture_data_api>` is meant to eventually catalog these files as data entities too -- a filesystem path, an S3 object, or a plain URL, with metadata validated against a JSON Schema rather than assumed to be DICOM-shaped -- but that work is still in progress. The Data API will not itself move or mount data between locations; getting bytes in or out of an external location is still the responsibility of the workflow's own operators.


