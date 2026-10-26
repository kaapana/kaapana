# @kaapana/extension-nninteractive

Kaapana OHIF extension for the nnInteractive segmentation workflow.

## Entry Points

| File | Role |
|---|---|
| `src/index.ts` | OHIF extension descriptor. Exposes pre-registration, commands, panels, customizations, and utilities. |
| `src/preRegistration.ts` | Runtime setup before modes enter: prompt-tool registration, icon registration, metadata providers, prompt-annotation stamping, the 3D-focus guard, the import-split hook, and viewport/session subscriptions. |
| `src/commandsModule.ts` | Thin nnInteractive command surface over the `model/` layer: session lifecycle, inference, undo/reset, manual correction, SEG store/download overrides (merged per-object → one overlapping SEG, with a series-name prompt on store), segment jumping/toggling. |
| `src/model/` | Product logic split by concern: `sessionModel`, `imageModel`, `objectModel`, `promptModel`/`promptDisplay`, `coordinateMapping`, `segmentationBridge` (the only module touching labelmap voxels; one OHIF segmentation per object + import-split), `serverApi`, `store`, `types`. |
| `src/getPanelModule.tsx` | Exposes `aiToolBox` and `panelSegmentationWithTools`. |
| `src/getCustomizationModule.ts` | Registers Cornerstone overlay/tool customizations. |
| `src/getUtilityModule.ts` | Exposes utility modules used by other package code. |

## Main Folders

| Folder | Role |
|---|---|
| `src/panels/` | AI toolbox panel plus extension-owned segmentation panel/table fork. |
| `src/tools/` | nnInteractive prompt tool subclasses (`Probe2`, `RectangleROI2`, `PlanarFreehandROI2`, `PlanarFreehandROI3`). |
| `src/icons/` | Icons registered with `Icons.addIcon(...)` in `preRegistration.ts`. |
| `src/customizations/` | Components plugged into OHIF customization slots. |
| `src/utils/` | Shared runtime helpers: toolbox state, multipart parsing, prompt-annotation styling, and measurement-state events. |

## Data Model & Workflow

**Prompts are locked Cornerstone annotations.** Each point/box/lasso/scribble is an annotation drawn
with one of the `Probe2`/`RectangleROI2`/`PlanarFreehandROI2`/`PlanarFreehandROI3` tools. `promptModel`
keeps a ledger of each prompt's positive/negative sign and submitted state; `preRegistration.ts`
stamps a prompt on draw and, in live mode, submits it on completion. `model/coordinateMapping.ts`
converts each annotation's geometry into the IJK payload the proxy expects, for both stack and MPR
planes.

**One OHIF segmentation per nnInteractive object.** Each object is its own segmentation with a single
labelmap and segment index 1, so objects overlap natively and render/edit in the stack view and the
axial/coronal/sagittal MPR views. `model/segmentationBridge.ts` is the only module that reads or
writes labelmap voxels: it keeps the native labelmap volume authoritative, mirrors it into the stack
labelmap, assigns each object a palette color, and drives MPR representation setup.

**Session & inference.** `sessionModel` owns the backend session lifecycle over the `serverApi`
facade; `objectModel` tracks the active object and its dirty state. Running the prompts sends them
through the proxy, which returns a cropped mask that `segmentationBridge` writes into the active
object. Manual brush edits mark the object dirty and are sent back to the backend as `set_mask` on
the next run.

**Import / export.** On load, a stored SEG that OHIF hydrates as one multi-segment segmentation is
split into per-object segmentations, preserving each segment's label and color. On store/download,
the per-object segmentations are merged into one overlapping DICOM SEG; store prompts for a series
name first.

## Command Ownership

This extension intentionally overrides or supplements some stock OHIF commands. Keep related command
families together:

- session commands: `initNninter`, `nninterSessionStatus`, `closeNninterSession`
- inference commands: `nninter` (run prompts), `undoNninter`, `resetNninter`, `resetSegment`, `deleteSegment`
- object commands: `armNextNninterObject`, `loadSegmentForRefinement`
- manual correction: brush add/erase in manual-correction mode; edits mark the active object dirty and go to the backend as `set_mask` on the next run
- UI bridge commands: `setAiToolActive`, `runAiSegmentation`
- navigation/visibility: `jumpToSegment`, `toggleCurrentSegment`
- SEG operations: `storeNninterSegmentation` and `downloadNninterSegmentation` merge the per-object segmentations into one overlapping DICOM SEG

Do not split store/download changes across extension and source patches unless there is no choice.
These flows share assumptions about segmentation ids, display sets, and the per-object labelmap layout.

## Prompt Tool Ownership

Prompt tool behavior lives in `src/tools/promptTools.ts`. The subclasses render prompt annotations
with pending/positive/negative styling and provide `_addNewAnnotationFromIndex(...)`;
`model/coordinateMapping.ts` converts each prompt annotation's geometry into the IJK payload the
proxy expects.

The remaining package-level prompt/rendering behavior in `../../node-module-patches` should only move
here after testing all prompt types:

- positive/negative point
- positive/negative box
- positive/negative scribble
- positive/negative lasso
- live mode

## Segmentation Table

`src/panels/SegmentationTable/` is a local fork of the relevant OHIF segmentation table pieces. This
is deliberate: the nnInteractive panel needs multi-select, per-object color and label, prompt cleanup,
and manual-correction ergonomics that are easier to reason about in an owned component tree.

When upstream OHIF changes its table, do not blindly copy the new version over this folder. First
check whether the change affects:

- visibility updates
- active segment selection
- per-object color and label
- prompt cleanup when segments/segmentations are removed
- manual correction brush add/erase workflows
- single-step nnInteractive undo; the backend can undo only the latest interaction
- per-tab nnInteractive session ids; one user's close request must not close another user's lease

## Runtime Assumptions

- The backend proxy is reachable under `/nninteractive/infer/...`.
- The proxy keys sessions by study, series, and the OHIF tab's `clientSessionID`.
- The mode registers the prompt tools in the active tool groups.
- The app config uses `activateViewportBeforeInteraction:false`; viewport hover activation is patched
  in `../../patches/30-nninteractive-ui.patch`.
- Cornerstone/vtk package patches are applied before the app build.

## Smoke Test After Changes

Verify:

- initialize/close session
- add all prompt types
- negative prompts subtract instead of add
- run segmentation and see mask update
- manual correction brush add/erase
- single-step undo/reset/next object
- store/export SEG (a series-name prompt appears before storing)
- reload stored SEG and see it split into per-object segmentations
- segment statistics display
