# dcm-mask-converter

Convert DICOM SEG / RTSTRUCT to NIFTI masks. Splits the two branches of the old `Mask2nifitiOperator` into separate templates.

## Templates needed

- `seg-to-nifti`: DICOM SEG -> NIFTI via `dcmqi`. Takes a `dicom` channel and a `reference` channel for spatial reference.
- `rtstruct-to-nifti`: DICOM RTSTRUCT -> NIFTI via `dcmrtstruct2nii`. Same input shape as `seg-to-nifti`.
