# nnunet

nnUNet v2 templates. Refactor of the multi-mode `NnUnetOperator`, each old `MODE` becomes its own template sharing the same `start_nnunet.sh` entrypoint.

## Templates needed

- `preprocess`: fingerprinting, planning, integrity check. Inputs: `images`, `labels`. Output: `dataset`. Replaces `NnUnetOperator(mode="preprocess")`.
- `train`: training (GPU, 11 GB). Inputs: `dataset`. Output: `model`. Replaces `NnUnetOperator(mode="training")`.

`inference`, `ensemble`, `install-model` should also be implemented in the future