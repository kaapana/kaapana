.. _storage:

Storage
*******

In general, the platform is a processing platform, which means that it is not a persistent data storage. Ideally, all the data on the platform should only form a copy of the original data.
Data that is in DICOM format is stored in an internal PACS called  *DCM4CHEE*.
For all non-DICOM data, an object store called *Minio* is available.
In Minio, arbitrary data files can be stored in buckets and are accessible via the browser for download.
Ideally the results of a workflow executed on the platform will be available as DICOM and stored in the PACS of the Platform where it can be accessed by via the existing tooling (e.g. Datasets View, Meta Dashboard).
However the DICOM format might not always be a good fit for results, therefore non-DICOM results are supported via Minio.
Sending DICOM images to platform (e.g. from a clinical PACS or a radiologists workstation) is possible via port ``11112``. Here a component called *Clinical Trial Processor (CTP)* takes care of receiving the images and then triggers the ingestion workflows.
DICOM Images can also be viewed directly in the OHIF Viewer. It can be found as *OHIF* under the *Store* menu.

If you are more interested in the technologies, you can get started here:

* `OpenSearch <https://opensearch.org/>`_
* `OpenSearch Dashboards <https://opensearch.org/docs/latest/dashboards/index/>`_
* `Minio <https://min.io/>`_
* `OHIF <https://ohif.org/>`_
* `Clinical Trial Processor (CTP) <https://mircwiki.rsna.org/index.php?title=CTP-The_RSNA_Clinical_Trial_Processor#Clinical_Trial_Processor_.28CTP.29>`_



