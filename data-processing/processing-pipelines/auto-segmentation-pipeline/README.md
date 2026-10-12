# Auto Segmentation Pipeline — integrating into an existing Kaapana platform

Two Airflow DAGs:

- **`auto-segmentation-pipeline`** — infers the body part a radiology (CT/MR) series covers from
  the DICOM metadata of the matching pathology (SM) study for the same patient, then runs
  TotalSegmentator v2 restricted to that one organ (`roi_subset`/`fast`) instead of the full
  117/50-structure set. This is the "segment the organ a pathology slide is actually about"
  step the split-viewer's organ-to-slide linking depends on.
- **`wsi-mapping-pipeline`** — repairs a radiology/pathology pair whose `PatientID`s don't match
  (e.g. from pseudonymization or separate DICOM conversion pipelines): rewrites the pathology
  series' DICOM tags to the radiology series' `PatientID` (and optionally `BodyPartExamined`),
  then re-imports it into the PACS so normal ingestion re-indexes it under the corrected tags.
  Run this once on a mismatched pair; after that, `auto-segmentation-pipeline`'s automatic
  inference just works on it.

This document is about getting it into a Kaapana platform that is **already built and running**.
If you're building the whole platform from scratch instead, nothing further is needed — this
extension is already registered in `collections/kaapana-collection/requirements.yaml`.

## What's inside

| Path | Builds into | Used by |
|---|---|---|
| `extension/docker/` | Docker image `dag-auto-segmentation-pipeline` | the Airflow DAG-installer Job |
| `extension/auto-segmentation-pipeline-workflow/` | Helm chart `auto-segmentation-pipeline-workflow` | installs/uninstalls the above |

Just one image — both DAGs only orchestrate *existing* operators (`GetInputOperator`,
`DcmSendOperator`, `DynamicConfDagTriggerOperator` triggering `total-segmentator-v2`/
`delete-series`), so there's no dedicated processing-container here.

**Note:** `auto-segmentation-pipeline` triggers the stock `total-segmentator-v2` DAG with
`roi_subset`/`fast` set in its conf. That requires the `roi_subset` field added to
`data-processing/processing-pipelines/total-segmentator-v2/extension/docker/files/dag_total_segmentator_v2.py`
and the parsing fix in
`.../total-segmentator-v2/processing-containers/total-segmentator/files/start-total-segmentator-v2.py`
— both already modified directly in the existing `total-segmentator-v2` extension (not part of
this one), so make sure that extension's DAG image and `total-segmentator-v2` container image are
also rebuilt/redeployed on your target platform, the same way as below.

## Option A — through the Extensions UI (recommended, Kaapana's own supported path)

Same process as `workflow_dev_guide.rst` Steps 4–9, applied here.

**0.** Get your platform's registry URL and version from the "About" page.

**1. Build**

```bash
export REGISTRY=<platform-registry-url>
export VERSION=<platform-version>
cd data-processing/processing-pipelines/auto-segmentation-pipeline
docker build -t $REGISTRY/dag-auto-segmentation-pipeline:$VERSION extension/docker
```

(needs `local-only/base-installer:latest` built first, same as any `dag-*` image)

**2. Push** (or save + upload via the Extensions UI if you don't have registry write access):

```bash
docker push $REGISTRY/dag-auto-segmentation-pipeline:$VERSION
```

**3. Package**

```bash
cd extension/auto-segmentation-pipeline-workflow
helm dep up
helm package .
```

**4. Install**: Extensions view → upload the `.tgz` → find
`auto-segmentation-pipeline-workflow` → Install. It's **experimental** — enable that Maturity
filter if it's not showing.

**5. Allow-list it**: System → Projects → your project → "Add Software to Project" →
`auto-segmentation-pipeline-workflow`.

**6. Run it**: from a radiology series in the Datasets view → Workflow Execution →
`auto-segmentation-pipeline` (auto-infers the body part) or `wsi-mapping-pipeline` (select both
the radiology and pathology series first, to repair a mismatched pair).

### Troubleshooting

- **`total-segmentator-v2` still segments all 117 structures instead of one organ**: this means
  the body part couldn't be inferred (check the `infer_body_part` task's logs — "Could not infer
  body part from SM metadata" means the pathology series' tags genuinely don't carry a
  recognizable body part, which is expected fallback behavior, not a bug) or `total-segmentator-v2`'s
  own image/DAG wasn't rebuilt with the `roi_subset`/`start-total-segmentator-v2.py` fix (see note
  above — that's a separate extension you need to redeploy too).
- **`roi_subset must be a list of strings`**: the `total-segmentator-v2` container image running on
  your platform doesn't have the parsing fix from
  `start-total-segmentator-v2.py` yet — rebuild/redeploy that image specifically.
- **`wsi-mapping-pipeline` succeeds but the pathology series still shows under the old `PatientID`**:
  check the `dcm_send` task's log for actual send confirmation, and confirm
  `trigger_delete_old_pathology_series`'s child `delete-series` run succeeded *before* the resend —
  the DAG deletes the stale, wrongly-tagged copy first on purpose, so a partial run can leave
  nothing behind until retried.
- **`ErrImagePull` on the install Job (`dag-auto-segmentation-pipeline` pod)**: the Job's image tag
  comes from the chart's own `Chart.Version` at packaging time, and via the vendored
  `dag-installer-chart` sub-chart's *own* `Chart.yaml` version (a separate file, since `.Chart` is
  chart-local in Helm) — make sure both are bumped to `$VERSION` before `helm dep up && helm package .`
  if they don't already match.

## Option B — direct deployment (fast iteration)

```bash
POD=$(kubectl get pods -n services --no-headers -o custom-columns=":metadata.name" | grep airflow-webserver | head -1)
kubectl exec -n services "$POD" -c webserver -- mkdir -p /kaapana/mounted/workflows/plugins/autosegmentationpipeline
kubectl cp extension/docker/files/dag_auto_segmentation_pipeline.py services/$POD:/kaapana/mounted/workflows/dags/dag_auto_segmentation_pipeline.py
kubectl cp extension/docker/files/dag_wsi_mapping.py services/$POD:/kaapana/mounted/workflows/dags/dag_wsi_mapping.py
kubectl cp extension/docker/files/autosegmentationpipeline/. services/$POD:/kaapana/mounted/workflows/plugins/autosegmentationpipeline/
```

Not a substitute for a real install (Option A) — this bypasses versioning and the DAG-installer
Job's bookkeeping entirely, so it won't survive a clean reinstall of the platform's DAG volumes.
