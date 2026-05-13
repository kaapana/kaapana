# mitk-tools

MITK-based image conversion and registration templates.

## Templates needed
- `convert` (DICOM → NRRD) and `register` templates come from the registration workflow and are implemented.
- `convert-to-nifti`: convert DICOM series to NIFTI (`.nii` / `.nii.gz`) via MITK FileConverter. Selectable variant via `OUTPUT_FORMAT` env. Replaces the NIFTI path of the old `DcmConverterOperator`. Used by nnunet-training (`ref_to_nifti` task).
