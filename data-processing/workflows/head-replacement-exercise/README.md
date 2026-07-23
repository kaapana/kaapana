# Head replacement Workflow API exercise

This directory is the starter project for the Geometric Heads hands-on guide.
It contains an OCI `workflow-v1` demo that replaces the BodyPartRegression head
region of CT volumes with a synthetic sphere.

Complete the two marked exercises before validating or building the project:

- define the task template in
  `processing-containers/head-demo-tools/processing-container.json`;
- connect the `replace_head` task in
  `oci/head-replacement/workflow_definition.py`.

The `processing-container.json` starter intentionally contains instructional
comments and is invalid JSON until the exercise is completed. The algorithm,
Dockerfile, task fixture, workflow metadata, and OCI manifest are provided.

Run the commands below from the root of the Kaapana checkout.

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
  --build-ignore-patterns "*templates_and_examples/*,*ci/*,*lib/task_api/*,head-replacement" \
  --containers-to-build head-demo-tools
```

The final ignore entry excludes the completed reference pipeline, which uses
the same image name as this exercise.

Alternatively, build and push the image directly with Docker. The
`local-only/base-python-cpu:latest` base image must already be available in the
local Docker daemon:

```bash
docker login REGISTRY_HOST --username USER

docker build \
  --tag REGISTRY/head-demo-tools:PLATFORM_VERSION \
  data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools

docker push REGISTRY/head-demo-tools:PLATFORM_VERSION
```

Replace `REGISTRY_HOST` with the registry hostname, `REGISTRY` with the image
prefix used by the platform, and `PLATFORM_VERSION` with the target platform's
`KAAPANA_BUILD_VERSION`.

Validate the custom Task API manifests and local fixtures with:

```bash
python3 -m task_api.cli validate \
  data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools/processing-container.json \
  --schema pc

python3 -m task_api.cli validate \
  data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools/tasks/replace-head-task.json \
  --schema task
```

Build and publish the OCI workflow artifact with:

```bash
extensionctl login --registry REGISTRY --repo REPOSITORY --user USER --password TOKEN
extensionctl build \
  data-processing/workflows/head-replacement-exercise/oci \
  --output data-processing/workflows/head-replacement-exercise/dist
extensionctl push \
  data-processing/workflows/head-replacement-exercise/dist/head-replacement-extension-v0.2.1.tar.gz
extensionctl list --full
```

Install the published extension through the Extension Manager UI or REST API.
