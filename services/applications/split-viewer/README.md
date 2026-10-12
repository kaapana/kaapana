# Split Viewer — integrating into an existing Kaapana platform

A split-screen web app linking a radiology study (OHIF) to its matching pathology slide (SLIM),
with click-to-segment organ linking: clicking "Segment" triggers `auto-segmentation-pipeline`,
and clicking a segmented organ in OHIF opens the matching pathology slide in SLIM next to it (via
`kaapana-backend`'s `/dataset/matching-sm-series` endpoint and the OHIF SEG-viewport patch in
`services/store/ohif-viewer`).

This document is about getting it into a Kaapana platform that is **already built and running**.
If you're building the whole platform from scratch instead, nothing further is needed — this
extension is already registered in `collections/kaapana-collection/requirements.yaml`.

Unlike `trident-wsi`/`auto-segmentation-pipeline`, this is **not** an Airflow DAG extension — it's
a standalone web application (a plain Kubernetes Deployment + Service + Ingress), so none of the
DAG-installer-chart/Extensions-view-upload machinery applies here. It's a direct Helm install.

## What's inside

| Path | Builds into |
|---|---|
| `docker/` | Docker image `split-viewer` (multi-stage: Vite/React frontend build, then a small Node/Express server that also proxies to `dicom-web-filter-service`/`kaapana-backend`) |
| `split-viewer-chart/` | Helm chart `split-viewer-chart` (Deployment, Service, Traefik `Middleware`+`Ingress` at `/split-viewer`) |

This feature also depends on changes in two *existing* platform components, which need to be
rebuilt/redeployed on your target platform too if you want the full click-to-segment flow (the
split-viewer app itself will still load and show both viewers without them, just without the
organ-click linking):

- `services/store/ohif-viewer` (`docker/files/customization.patch`) — adds the SEG-viewport click
  handler that `postMessage`s the clicked segment's label to the embedding page.
- `services/base/kaapana-backend` (`docker/files/app/datasets/body_part_matching.py`,
  `routers.py`) — the `/dataset/matching-sm-series` endpoint the split-viewer's frontend calls.

## Build and install

**0.** Get your platform's registry URL and version from the "About" page, and the
`services`-namespace node name Kubernetes reports for your main node
(`kubectl get nodes` — only relevant if you need `nodeSelector`-style targeting; this chart
itself doesn't require it).

**1. Build**

```bash
export REGISTRY=<platform-registry-url>
export VERSION=<platform-version>
cd services/applications/split-viewer
docker build -t $REGISTRY/split-viewer:$VERSION docker
```

**2. Push**

```bash
docker push $REGISTRY/split-viewer:$VERSION
```

(No registry write access? Save with `docker save $REGISTRY/split-viewer:$VERSION -o split-viewer.tar`
and upload via the Extensions view's "Upload chart or container files" the same way as any other
image — that mechanism isn't specific to DAG extensions.)

**3. Install**

```bash
helm upgrade --install split-viewer-chart ./split-viewer-chart \
  --namespace services \
  --set global.registry_url=$REGISTRY \
  --set global.kaapana_build_version=$VERSION \
  --set global.services_namespace=services \
  --set global.pull_policy_pods=Always
```

If your registry needs a pull secret that isn't already named `registry-secret` on your platform
(e.g. you're pushing to a personal/secondary registry during development, not the platform's own
one), add it explicitly — the chart's default is only what a real deployment against the
platform's own registry needs:

```bash
  --set "global.image_pull_secrets={registry-secret,<your-extra-secret>}"
```

**4. Open it**: `https://<your-kaapana-domain>/split-viewer`.

There's no project allow-listing step for this one — it's a standalone application (not something
triggered per-project via the workflow-execution UI), so it's reachable directly once installed.
It does rely on the Datasets view to launch it with a study selected, same as any other viewer
integration.

## Verifying the full flow

1. Open the split-viewer on a radiology (CT/MR) series that has a matching pathology (SM) series
   for the same patient.
2. Click "Segment" — this triggers `auto-segmentation-pipeline` (needs that extension installed
   too, see its own README).
3. Once segmentation finishes, open the radiology side in OHIF, click a segmented organ:
   - if a pathology slide exists for that organ, SLIM opens showing it.
   - if you click an organ this patient has no matching slide for, nothing should open (there's
     deliberately no "first slide found" fallback — only the genuinely matching organ is
     clickable).

## Troubleshooting

- **`ErrImagePull`/`ImagePullBackOff`**: check `kubectl get deployment split-viewer -n services -o
  jsonpath='{.spec.template.spec.containers[0].image}'` matches what you actually pushed. A stale
  cached image on the node (same tag, different digest) can also cause this — purge it with
  `kubectl exec`-equivalent node tooling (e.g. `microk8s ctr images rm
  $REGISTRY/split-viewer:$VERSION`) and let it re-pull.
- **`helm upgrade` runs but the pod doesn't pick up a rebuilt image**: `helm upgrade`/`kubectl set
  image` only triggers a new rollout when the image *string* changes — rebuilding under the same
  tag is a silent no-op. Force it: `kubectl rollout restart deployment/split-viewer -n services`.
- **Clicking a segmented organ does nothing, even for an organ that should match**: confirm the
  OHIF image deployed on your platform actually has the `customization.patch` changes baked in
  (check the browser console for the `ohif-segment-click` postMessage — if it never fires, OHIF's
  own image wasn't rebuilt/redeployed) and that `kaapana-backend`'s image has the
  `/dataset/matching-sm-series` endpoint (same check, server-side: `curl` it directly with a known
  `study_instance_uid`/`label`).
