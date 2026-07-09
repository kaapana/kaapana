.. _concepts_file_types:

File Types
################################

How is data ingested into Kaapana and what file types are supported?

Files
============================

Binary models, documents, PDFs, and other non-DICOM files are uploaded
through the **MinIO** web interface (see :ref:`store`), where they land in a
bucket and are managed as ordinary objects. Workflows access them through the
same underlying storage.

DICOM
========
DICOM file is stored in the internal PACS via DIMSE C-STORE or DICOMweb STOW-RS.
Both paths converge on the :ref:`Clinical Trial Processor (CTP)<store>`, which receives
the DICOM before the :ref:`service-process-incoming-dcm<service_process_incoming_dcm>` ingestion workflow (Airflow DAG) picks it up, validates it, extracts and indexes metadata, sets the correct access rights for the series, and creates a thumbnail. Other automatic pipelines can be autotriggered  here — pseudoanonymization, whole-slide
microscopy conversion, or radiomics feature extraction. The ingestion DAG
then hands the DICOM off to the PACS for storage and indexing.


Data API (Work in Progress)
===============================

The :ref:`Data API<concepts_architecture_data_api>` will eventually catalog
all file types as data entities — a filesystem path, an S3
object, PACS coordinates, or a plain URL — with metadata validated against a JSON Schema. Workflow will be responsible for getting the data from the coordinates provided by the Data API. This gives all file types the same guarantees: schema-validated metadata, a stable identifier, and discoverability.


