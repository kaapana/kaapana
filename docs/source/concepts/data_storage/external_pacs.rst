.. _concepts_external_pacs:

External PACS
################################

Connecting to a DICOM node (PACS) is done platform-wide, through the :ref:`DICOM Web Filter<concepts_architecture_dicom_web_filter>`. It is configured with a single DICOMweb base URL, pointed at the internal PACS by default. Because this is a plain endpoint URL, it can instead be pointed at an external DICOMweb-compliant store, making that store the one Kaapana ingests from and queries against, in place of the local dcm4chee PACS.

This one setting governs every DICOM consumer on the platform -- ingestion, the Gallery View, OHIF, Slim Viewer -- since they all resolve DICOM through the DICOM Web Filter rather than each maintaining its own PACS connection. Retargeting the platform to an external archive is therefore a single Helm value, not a per-component migration.

The cost of that convenience is granularity: the redirect applies to the whole platform at once. There is currently no way to serve one project from the internal PACS and another from an external archive at the same time.
