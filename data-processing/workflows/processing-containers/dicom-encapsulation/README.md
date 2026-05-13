# dicom-encapsulation

Wrap non-DICOM payloads into DICOM objects via DCMTK. Clusters the two old `*2Dcm` operators since they share the same toolchain.

## Templates needed

- `pdf-to-dicom`: encapsulate a PDF as DICOM Encapsulated PDF Storage using `pdf2dcm`. Replaces `Pdf2DcmOperator`.
- `binary-to-dicom`: encapsulate arbitrary binary blobs as DICOM via `xml2dcm`, with chunking by `SIZE_LIMIT_MB`. Replaces `Bin2DcmOperator`.
