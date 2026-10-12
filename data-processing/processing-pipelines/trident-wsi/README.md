# TRIDENT WSI — integrating into an existing Kaapana platform

This extension adds two Airflow DAGs, `trident-tissue-segmentation` and
`trident-feature-extraction`, that run the [TRIDENT](https://github.com/mahmoodlab/trident)
whole-slide-image pipeline (tissue segmentation visualized in SLIM as a Comprehensive 3D SR, and
foundation-model feature extraction) against DICOM WSI series.

This document is about getting it into a Kaapana platform that is **already built and running**
(no rebuild of the whole platform). If you're building the whole platform from scratch instead,
nothing further is needed here — this extension is already registered in
`collections/kaapana-collection/requirements.yaml` and gets picked up automatically.

## What's inside

| Path | Builds into | Used by |
|---|---|---|
| `extension/docker/` | Docker image `dag-trident-wsi` | the Airflow DAG-installer Job (copies the DAG files into Airflow) |
| `extension/trident-wsi-workflow/` | Helm chart `trident-wsi-workflow` | installs/uninstalls the above into the platform |
| `processing-containers/trident/` | Docker image `trident` | the actual GPU-based segmentation/feature-extraction step (`TridentSegmentationOperator`, `TridentFeatureExtractionOperator`, `TridentPatchingOperator`) |
| `processing-containers/trident-dicom-utils/` | Docker image `trident-dicom-utils` | DICOM-level glue: GeoJSON↔DICOM-SR conversion, feature encapsulation (`GeojsonToSROperator`, `EncapsulateFeaturesDicomOperator`) |

Three images total, one chart.

## Option A — through the Extensions UI (recommended, this is Kaapana's own supported path)

This follows Kaapana's documented workflow-extension process
(`docs/source/development_guide/workflow_dev_guide.rst`, Steps 4–9), applied to this extension.

**0. Get your platform's registry URL and version**

In the Kaapana UI, open the "About" page — note the registry URL and the platform version
(e.g. `registry.example.com/kaapana`, `0.6.1`). Use these exact values below as
`$REGISTRY`/`$VERSION`.

**1. Build the three images**

```bash
export REGISTRY=<platform-registry-url>
export VERSION=<platform-version>
cd data-processing/processing-pipelines/trident-wsi

docker build -t $REGISTRY/dag-trident-wsi:$VERSION extension/docker
docker build -t $REGISTRY/trident:$VERSION processing-containers/trident
docker build -t $REGISTRY/trident-dicom-utils:$VERSION processing-containers/trident-dicom-utils
```

(`trident`'s Dockerfile needs `local-only/base-python-gpu:latest`, `trident-dicom-utils`'s needs
`local-only/base-python-cpu:latest`, and `dag-trident-wsi`'s needs `local-only/base-installer:latest`
— build these three base images first if they aren't already on your machine; see
`data-processing/base-images/base-python-cpu`, `.../base-python-gpu`, `services/utils/base-installer`.)

**2. Get the images into the platform**

If you have push access to `$REGISTRY`:

```bash
docker push $REGISTRY/dag-trident-wsi:$VERSION
docker push $REGISTRY/trident:$VERSION
docker push $REGISTRY/trident-dicom-utils:$VERSION
```

If you don't, save them and upload through the UI instead:

```bash
docker save $REGISTRY/dag-trident-wsi:$VERSION $REGISTRY/trident:$VERSION $REGISTRY/trident-dicom-utils:$VERSION -o trident-wsi-images.tar
```

Then: Extensions view → "Upload chart or container files" → upload `trident-wsi-images.tar`.

**3. Package the Helm chart**

```bash
cd extension/trident-wsi-workflow
helm dep up
helm package .
```

This produces `trident-wsi-workflow-<chart-version>.tgz`. Whatever version ends up in that
filename must match an image tag that actually exists at `$REGISTRY` (see Troubleshooting below
if it doesn't line up).

**4. Install**

Extensions view → "Upload chart or container files" → upload the `.tgz` → find
`trident-wsi-workflow` in the extension list → Install.

Since this extension isn't an official release yet, it's marked **experimental** — select
"Experimental" under the Maturity filter if it doesn't show up.

**5. Allow-list it for your project**

Required since Kaapana `0.5.0`: System → Projects → select your project → "Add Software to
Project" → select `trident-wsi-workflow`.

**6. Run it**

From the Datasets view, select a WSI (SM-modality) series → Workflow Execution →
`trident-tissue-segmentation` (to get a SLIM-viewable segmentation) and/or
`trident-feature-extraction`.

### Troubleshooting

- **`ErrImagePull`/`ImagePullBackOff` on the `trident` or `trident-dicom-utils` pod**: the operator's
  own image reference (`TridentSegmentationOperator.py` etc.) is built from
  `{DEFAULT_REGISTRY}/<image>:{KAAPANA_BUILD_VERSION}` — these are the running platform's own
  globals, not anything you set locally. Confirm the image was actually pushed/uploaded under the
  exact registry+version your platform reports on its "About" page.
- **`ErrImagePull` on the install Job itself (pod named `dag-trident-wsi` or similar, visible briefly
  in the Kubernetes view right after clicking Install)**: this Job's own image tag comes from the
  *chart's* version (`.Chart.Version`, i.e. `trident-wsi-workflow/Chart.yaml`'s `version:` field at
  packaging time), not `$VERSION` directly. If `helm package .` produced a `.tgz` with a version
  that doesn't match the `dag-trident-wsi` tag you actually pushed (e.g. it packaged as `0.0.0`
  because `Chart.yaml` still says `version: "0.0.0"`), edit `Chart.yaml`'s `version:` field (and,
  since the vendored `dag-installer-chart` dependency's own `Chart.yaml` version is what the install
  Job's image tag is actually templated from — it's a separate chart, so `.Chart.Version` inside
  *its* own template resolves to *its own* `Chart.yaml`, not this one — you may need to bump
  `services/utils/dag-installer-chart/Chart.yaml`'s version too, in your local checkout only, before
  running `helm dep up`) to match `$VERSION`, then repackage.
- **GPU scheduling**: the `trident` container needs a GPU-capable node. If your platform is
  single-node with a GPU, this is automatic; on a multi-node cluster, confirm the node has the
  right GPU labels/taints.
- **Debugging a failed task**: use Kaapana's code-server debug flow (see `workflow_dev_guide.rst`,
  Step 9) — add `dev_server="code-server"` to the failing operator's instantiation, redeploy, and
  open it from Active Applications.

## Option B — direct deployment (fast iteration, what was used to develop this extension)

For quick local iteration against an already-running dev cluster, you can skip the chart/Job
machinery entirely: build+push the three images as in Option A step 1–2, then copy the DAG files
directly into Airflow's own mounted volumes (the exact thing the install Job in Option A would do
for you, just done by hand):

```bash
POD=$(kubectl get pods -n services --no-headers -o custom-columns=":metadata.name" | grep airflow-webserver | head -1)
kubectl exec -n services "$POD" -c webserver -- mkdir -p /kaapana/mounted/workflows/dags/trident_ops
kubectl cp extension/docker/files/dag_trident_tissue_segmentation.py services/$POD:/kaapana/mounted/workflows/dags/dag_trident_tissue_segmentation.py
kubectl cp extension/docker/files/dag_trident_feature_extraction.py services/$POD:/kaapana/mounted/workflows/dags/dag_trident_feature_extraction.py
kubectl cp extension/docker/files/trident_ops/. services/$POD:/kaapana/mounted/workflows/dags/trident_ops/
```

This is **not** a substitute for a real install — it bypasses versioning and won't survive a
`helm uninstall`/reinstall of the platform's DAG volumes. Use Option A for anything meant to
persist or be shared.
