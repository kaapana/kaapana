# OHIF viewer image with nnInteractive

This directory builds Kaapana's OHIF viewer image with the nnInteractive segmentation workflow.
The build starts from a pristine upstream OHIF checkout, then layers Kaapana-owned extension/mode
packages and the small set of remaining in-place patches needed for this OHIF/Cornerstone version.

## Build Shape

| Path | Purpose |
|---|---|
| `Dockerfile` | Fetches upstream OHIF, applies source patches, copies local packages/config, applies dependency patches, builds the static viewer, and serves it with nginx. |
| `packages/extension-nninteractive/` | Kaapana OHIF extension that owns nnInteractive behavior: a `model/` layer (session, image, object, prompt, coordinate-mapping, segmentation-bridge) under a thin command layer, plus panels, prompt-tool subclasses, customizations, icons, metadata providers, and runtime subscriptions. |
| `packages/mode-nninteractive/` | Kaapana OHIF mode that owns layout, toolbar sections/buttons, hotkeys, and tool-group setup for the nnInteractive workflow. |
| `patches/` | Remaining source patches applied to the fetched OHIF tree with `git apply`. These are intentionally small residue, not the main feature implementation. |
| `node-module-patches/` | `patch-package` diffs for pinned Cornerstone/vtk packages. These are low-level runtime fixes that cannot cleanly live in an OHIF extension. |
| `files/customization.patch` | Kaapana viewer integration patch: embedding flags, SEG/RT auto-hydration, app robustness guards. |
| `files/kaapana.js` | Runtime OHIF app config. Copied to both `public/config/kaapana.js` during build and final `/ohif/app-config.js`. |
| `pluginConfig.json` | Registers the local extension and mode plus the required stock OHIF plugins. |
| `yarn.lock` | Frozen dependency tree. Must stay in sync with `00-deps-build.patch` and `node-module-patches/`. |
| `conf/` | nginx configuration for the final image. |

## Version Pins

The Dockerfile pins upstream OHIF with:

- `OHIF_VERSION=3.10.4`
- `OHIF_COMMIT=d383be7c720ec61f5bb1262ebe70893873718951`

The dependency tree currently pins the package-patched runtime surface to:

- `@cornerstonejs/core@3.33.5`
- `@cornerstonejs/tools@3.33.5`
- `@kitware/vtk.js@32.12.0`

The Dockerfile checks these exact versions before running `patch-package`, so dependency drift fails
early instead of producing a subtly broken viewer.

## Ownership Rules

- Put nnInteractive product behavior in `packages/extension-nninteractive`.
- Put workflow wiring, toolbar controls, hotkeys, and tool groups in `packages/mode-nninteractive`.
- Keep `patches/` for unavoidable source-tree residue: build/dependency changes, tiny OHIF hooks, or
  correctness fixes that have no extension seam in OHIF 3.10.
- Keep `node-module-patches/` for low-level Cornerstone/vtk rendering, labelmap, geometry, and worker
  fixes that cannot be expressed through OHIF extension APIs.

When in doubt, prefer extension/mode code over source patches, and prefer small documented patches
over runtime monkey-patching of third-party internals.

## Build

```bash
docker build -t registry.hzdr.de/benjamin.hamm/kaapana-bhamm-dev/ohif:<tag> .
```

## Deploy Locally

The local cluster has historically used namespace `services` and deployment `ohif`:

```bash
docker push registry.hzdr.de/benjamin.hamm/kaapana-bhamm-dev/ohif:<tag>
microk8s kubectl -n services set image deployment/ohif \
  '*=registry.hzdr.de/benjamin.hamm/kaapana-bhamm-dev/ohif:<tag>'
microk8s kubectl -n services rollout status deployment/ohif --timeout=180s
```

## Test

After each patch/package change, verify at least:

- open viewer and load a study
- initialize nnInteractive session
- add positive and negative point prompts
- add box, scribble, and lasso prompts
- run segmentation and confirm mask updates
- use manual correction brush in add and erase mode
- undo/reset/next object
- store/export SEG (a series-name prompt appears before storing)
- reload stored SEG and confirm it splits back into per-object segmentations for further refinement
- segment statistics display

## Upgrade Checklist

1. Bump `OHIF_VERSION` and `OHIF_COMMIT` in `Dockerfile`.
2. Re-apply or regenerate `patches/*.patch` against the new upstream tree.
3. Run `yarn install` only intentionally; update `yarn.lock` and `00-deps-build.patch` together.
4. If Cornerstone/vtk versions change, regenerate `node-module-patches/` for the new package versions.
5. Build the image.
6. Run the smoke test above before deploying broadly.
