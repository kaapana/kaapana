.. _concepts_external_pacs:

External PACS
################################

Connecting to a DICOM node (PACS) is done platform-wide, through the :ref:`DICOM Web Filter<concepts_architecture_dicom_web_filter>`. It is configured with a single DICOMweb base URL, pointed at the internal PACS by default. Because this is a plain endpoint URL, it can instead be pointed at an external DICOMweb-compliant store, making that store the one Kaapana ingests from and queries against, in place of the local dcm4chee PACS.
