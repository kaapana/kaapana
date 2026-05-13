# seg-check

Validate NIFTI segmentation masks against a paired reference image. Replaces `SegCheckOperator`. Kept separate from `mask-processing` because it requires a reference channel and does heavier numerical work (resampling).

## Templates needed

- `seg-check`: resample masks to reference space, check overlap percentage, label consistency, label-id extractability. Inputs: `masks`, `reference`. Output: `checked-masks`.
