# OHIF viewer image (nnInteractive)

This image builds the OHIF viewer used by Kaapana, including the **nnInteractive**
interactive-AI-segmentation feature. It is **not** a vendored fork: pristine upstream OHIF
is fetched at build time and our changes are layered on top as patches.

## Build inputs (in this directory)

| Path | Purpose |
|---|---|
| `Dockerfile` | Fetches pristine OHIF, applies the patches, builds, serves via nginx. |
| `patches/` | The CCI-Bonn/OHIF-AI fork's **source delta** vs pristine OHIF (nnInteractive feature + supporting edits), split by concern and applied in order with `git apply`. See `patches/README.md`. |
| `yarn.lock` | The fork's resolved dependency tree (pins Cornerstone 3.33.5 etc.). `yarn install --frozen-lockfile` reproduces it exactly — required because `node-module-patches/` are version-specific. |
| `files/customization.patch` | Kaapana customizations on top of the fork: embedding toggles (`showHeader`/`showLeftPanel`/`showRightPanel`), SEG/RT auto-hydration, robustness guards. |
| `node-module-patches/` | OHIF-AI modifications to **Cornerstone3D / vtk.js** dependency internals (prompt tools + labelmap update path), as readable, version-named `patch-package` diffs applied to `node_modules` after `yarn install`. Replaces the former opaque `backup/` file overwrites. (dcmjs override dropped — stock provides `SegmentDescription`.) |
| `pluginConfig.json` | Which OHIF extensions/modes are compiled into the app. |
| `files/kaapana.js` | OHIF app config (data sources, hotkeys, embedding flags). Becomes `app-config.js`. |
| `conf/` | nginx config. |

## OHIF version

Pinned via the `OHIF_COMMIT` build arg to `d383be7c…` — the fork's exact base
(2 trivial commits behind upstream tag `v3.10.4`). Building fetches this commit from
`github.com/OHIF/Viewers` (build-time network access required).

## Upgrading OHIF

1. Bump `OHIF_COMMIT` in the `Dockerfile`.
2. Re-validate `patches/*.patch` and `files/customization.patch` apply (regenerate hunks if upstream moved the touched files).
3. If the resolved `@cornerstonejs/*` / `@kitware/vtk.js` version changes, `patch-package` will fail loudly — regenerate `node-module-patches/` for the new version (install deps, re-apply the changes, `npx patch-package <pkg> --patch-dir node-module-patches`) and rename the patch files.
4. Rebuild and run the nnInteractive parity test (prompt tools, run segmentation, reopen a saved SEG to confirm prompt reconstruction).

> Longer term, the additive nnInteractive code in `ohif-ai.patch` (commands, Toolbox,
> toolbar) is being extracted into a standalone `@kaapana/extension-nninteractive` so the
> patch shrinks to only unavoidable in-place edits.
