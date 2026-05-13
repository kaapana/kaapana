# mask-processing

Clusters three label-manipulation steps that all operate on NIFTI segmentation masks plus their `seg_info.json` / `*-meta.json` sidecars (shared numpy / nibabel toolchain).

## Templates needed

- `filter-labels`: Keep/Ignore label filter on NIFTI masks. Replaces `LocalFilterMasksOperator`.
- `merge-masks`: combine or fuse multiple NIFTI masks into one; mode selected via `MERGE_MODE` env. Replaces `MergeMasksOperator`.
- `rename-labels`: apply `OLD_LABELS` -> `NEW_LABELS` mapping to filenames and JSON metadata. Replaces `LocalModifySegLabelNamesOperator`.
