# Classification workflow

This directory contains the Task API version of the classification workflow. It provides two workflows:

- `classification-training` trains a ResNet18 classifier on tagged DICOM series.
- `classification-inference` tags DICOM series with a trained model.

Both workflows are packaged as one OCI extension for the experimental extension manager
(`classification-workflow-extension/`). The legacy version under
`data-processing/processing-pipelines/classification-workflow/` still exists.

## Workflows

```
classification-training

download ──▶ convert ──▶ preprocessing ──▶ training ──▶ persist-model
  (dicom)     (nrrd)     (preprocessed)     (model)


classification-inference

download ──▶ convert ──▶ preprocessing ──▶ inference
                              ▲                ▲
model-download ──(model)──────┴────────────────┘
```

| Task | Image | Template | Purpose |
|---|---|---|---|
| `download` | `get-input-task` | `dicom-download` | Downloads the DICOM series of the selected dataset. |
| `convert` | `mitk-tools` | `convert` | Converts every series to nrrd. |
| `preprocessing` | `classification-preprocessing-task` | `preprocess` | Resizes every image to the patch size and normalizes it. |
| `training` | `classification-training-task` | `train` | Trains the model with the tags from OpenSearch as labels. |
| `persist-model` | `persist-model` | `persist` | Stores the model in the models volume and registers it in kaapana-backend. |
| `model-download` | `model-download` | `download` | Copies the selected model from the models volume. |
| `inference` | `classification-inference-task` | `infer` | Predicts a class for every series and adds it as a tag in OpenSearch. |

The tasks pass data through Task API input and output channels. Only `persist-model` and `model-download` access
the models volume directly.

## Model life cycle

1. `training` writes `model-best.pth.tar`, `model-end.pth.tar`, `config.json` and `training.log` to its `model`
   output. The model name in `config.json` is the name from the form plus a UTC timestamp, for example
   `resnet18-20261012-142233`. TensorBoard logs go to `/tensorboard/classification-training/<model name>`.
2. `persist-model` copies the model to `/models/classification-training/<model name>-fold-0/`. Then it registers
   all models in `/models/classification-training/` in kaapana-backend (`PUT /client/installed_models/sync`, kind
   `classification`). This request replaces the registered classification models of the project.
3. The model picker in the workflow UI lists the registered models (`GET /client/installed_models`). The selected
   value is the `task_ids` of the model, for example `resnet18-20261012-142233-fold-0/model-best.pth.tar`.
4. `model-download` checks the value and copies `config.json` and the checkpoint to its `model` output.
   `preprocessing` reads the patch size from `config.json`, and `inference` loads the checkpoint.

The models and TensorBoard volumes belong to the project namespace, so every project sees only its own models.
Both containers that access OpenSearch resolve the index of the project from `KAAPANA_PROJECT_IDENTIFIER`.

## Parameters

| Workflow | Parameter | Task | Description |
|---|---|---|---|
| training | `DATASET` | `download` | Dataset with the tagged series. |
| training | `TAG_TO_CLASS_MAPPING_JSON` | `training` | Comma-separated tags that are used as classes, at least two. |
| training | `TASK` | `training` | `binary`, `multiclass` or `multilabel`. |
| training | `DIMENSIONS` | `training` | `2D` or `3D`. |
| training | `PATCH_SIZE` | `preprocessing` | Shape that every image is resized to. Training reads it from the preprocessed images. |
| training | `BATCH_SIZE` | `training` | Batch size. |
| training | `NUM_EPOCHS` | `training` | Number of epochs. |
| training | `MODEL_CHECKPOINT_NAME` | `training` | Model name. Lowercase letters, digits, `-` and `_`. |
| inference | `DATASET` | `download` | Dataset that is tagged. |
| inference | `TAG_POSTFIX` | `inference` | Appends the model name, the fold and the checkpoint kind to the tag. |
| inference | `TASK_IDS` | `model-download` | Model from the model picker (form type `model`, kind `classification`). |

## Build and install

The platform build only builds containers that a Helm chart references. This extension has no Helm chart, so a
platform build or release does not contain its containers. Build and push them by hand, then publish the
extension.

1. Build the five processing containers and push them to the registry of the platform. Use the same commit as the
   platform build, because the DAGs pull `<registry>/<image>:<platform build version>`.

   ```bash
   kaapana-build --default-registry <registry> \
     --containers-to-build classification-preprocessing-task \
     --containers-to-build classification-training-task \
     --containers-to-build classification-inference-task \
     --containers-to-build persist-model \
     --containers-to-build model-download
   ```

   The workflows also use `get-input-task` and `mitk-tools`. These containers are part of every platform build.

2. Build the extension and push it to an OCI registry with `extensionctl` (see `lib/kaapana_extensions/README.md`):

   ```bash
   extensionctl login --registry <url> --repo <repo> --user <user> --password <password>
   extensionctl build data-processing/workflows/classification-workflow/classification-workflow-extension --push
   ```

3. In the extension manager, add the registry under **Repositories**. Then install
   `classification-workflow-extension` from the **Catalog**.

## Known limitations

- The legacy workflow writes its models to the same directory. They appear in the model picker, but the inference
  task cannot use them, because their `config.json` stores the name as `WORKFLOW_ID`.
- `KaapanaTaskOperator` mounts the `models-pv-claim` and `tensorboard-pv-claim` volumes of the project into every
  task pod. A task pod in a namespace without these volumes stays `Pending`.
- No GPU is requested for `training` and `inference`. The GPU base image sets `NVIDIA_VISIBLE_DEVICES=all`, so the
  pods can use all GPUs of the node, and the platform does not assign GPUs to runs.
- kaapana-backend requires unique model names across all projects. The timestamp makes a collision unlikely.
- `inference` uses the first output of the network for every task type. Results for `multiclass` and `multilabel`
  models are therefore not correct.
- With a batch size greater than one, `inference` skips the last incomplete batch.
