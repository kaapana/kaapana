# Head replacement Workflow API extension

This directory contains an OCI `workflow-v1` demo that replaces the
BodyPartRegression head region of CT volumes with a synthetic sphere.

## Workflow

| Task | Image / template | Input mapping | Output |
|---|---|---|---|
| `download_dataset` | `get-input-task` / `dicom-download` | none | `downloads` |
| `convert_to_nrrd` | `mitk-tools` / `convert` | `downloads` -> `dicom` | `nrrd` |
| `localize_head` | `bodypartregression-task-api` / `predict-body-parts` | `nrrd` -> `nrrd` | `bpr-json` |
| `replace_head` | `head-demo-tools` / `replace-head` | `nrrd` and `bpr-json` | `nrrd` |
| `convert_to_derived_dicom` | `nrrd-to-dicom` / `nrrd-to-dicom` | modified `nrrd` plus `downloads` -> `reference` | `dicom` |
| `send_derived_dicoms` | `send-dicoms` / `send-dicoms` | `dicom` -> `dicoms` | none |

All channels retain the `<channel>/<SeriesInstanceUID>/...` item layout. The
MITK-produced NRRD is passed directly to BodyPartRegression and the replacement
task. Both custom tasks orient the image to LPS consistently; BPR uses a
temporary NIfTI internally but does not expose a NIfTI channel.
The `head-demo-tools` command receives the two input `mounted_path` values and
the output `mounted_path` explicitly as CLI arguments.

The input dataset selector targets `download_dataset.DATASET`. The output
dataset field targets `send_derived_dicoms.DATASET` and is limited to 13
characters so the sender's `kp-` calling AE remains a valid DICOM AE title. The
reused sender is intentionally configured like the Registration Workflow demo:

- `PROJECT_NAME=admin`
- `PACS_HOST=ctp-dicom-service.services.svc`
- `PACS_PORT=11112`
- pod label `network-access-ctp=true`

Consequently, this demo writes to the selected dataset in the admin project.
A failed upstream task prevents the sender from starting; Airflow retries only
the sender and reuses the DICOM files already produced by the writer.

## Images

The target platform must provide Workflows V2 and the four reused Registration
Workflow images:

- `get-input-task`
- `mitk-tools`
- `nrrd-to-dicom`
- `send-dicoms`

as well as the `bodypartregression-task-api` image. This image must be built
and pushed separately; see the
[BodyPartRegression task README](../../kaapana-plugin/processing-containers/bodypart-regression-task/README.md).

Build and push the image with Kaapana's build CLI:

```bash
python3 -m pip install -e build_cli/
kaapana-build \
  --default-registry REGISTRY \
  --registry-username USER \
  --registry-password TOKEN \
  --build-ignore-patterns "*templates_and_examples/*,*ci/*,*lib/task_api/*" \
  --containers-to-build head-demo-tools
```
Validate the custom Task API manifests and local fixtures with:

```bash
python3 -m task_api.cli validate \
  processing-containers/head-demo-tools/processing-container.json \
  --schema pc

python3 -m task_api.cli validate \
  processing-containers/head-demo-tools/tasks/replace-head-task.json \
  --schema task
```

Build and publish the OCI workflow artifact with:

```bash
extensionctl login --registry REGISTRY --repo REPOSITORY --user USER --password TOKEN
extensionctl build ./oci --output ./dist
extensionctl push ./dist/head-replacement-extension-v0.2.1.tar.gz
extensionctl list --full
```

Install the published extension through the Extension Manager UI or REST API.
