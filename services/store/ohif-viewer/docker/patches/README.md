# OHIF-AI source patches

These patches are applied (in filename order) with `git apply` to a **pristine** upstream
OHIF checkout at build time — see the parent `Dockerfile`. Together they reproduce the
CCI-Bonn/OHIF-AI fork's source delta vs pristine OHIF `d383be7c` (the additive nnInteractive
feature + its supporting in-place edits). They are split by concern so each piece can be
reviewed and re-validated independently when upgrading OHIF.

The combined result is byte-for-byte identical to the historical single `ohif-ai.patch`.

| Patch | Concern |
|---|---|
| `00-deps-build.patch` | `package.json` deps + the root **`resolutions`** block (pins Cornerstone 3.33.5, react-router 6.30.4, …), `lerna.json`, `rsbuild`/`.webpack`/babel build config, `tailwind.css`. Must match the shipped `yarn.lock`. |
| `10-nninteractive-app.patch` | The additive nnInteractive app code in `extensions/default`: the `nninter*` commands (`commandsModule.ts`), the `Toolbox`, `toolboxState`, `multipart` parser. |
| `20-nninteractive-cornerstone.patch` | `extensions/cornerstone` + `cornerstone-dicom-seg` integration: segmentation/measurement services, panel, measurement mappings, prompt-tool toolnames. |
| `30-nninteractive-ui.patch` | `platform/ui-next` / `platform/ui`: prompt-tool icons + registry, SegmentationTable / DataRow multi-select & measurement-visibility UI. |
| `40-platform-core.patch` | `platform/core` + `platform/app`: MeasurementService methods, hotkeys, MetadataProvider, viewport grid. |
| `50-mode.patch` | `modes/longitudinal`: the `aiToolBox` toolbar section, prompt-tool buttons, tool-group registration. |
| `60-version-bump.patch` | `version.json` / `version.txt` string bumps (cosmetic). |

## Upgrading OHIF

Bump `OHIF_COMMIT` in the `Dockerfile`, then re-validate each patch applies (regenerate the
hunks for any whose target files upstream moved). The dependency layer (`00`) must stay in
sync with `../yarn.lock` and the `../node-module-patches/` Cornerstone/vtk patches (currently 3.33.5 / 32.12.0).
