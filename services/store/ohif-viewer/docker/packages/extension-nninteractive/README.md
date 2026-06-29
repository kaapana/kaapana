# @kaapana/extension-nninteractive

Kaapana OHIF extension for the nnInteractive segmentation workflow.

This package owns product behavior. If a change is about talking to the nnInteractive backend,
creating or reading prompts, showing the AI toolbox, managing nnInteractive segment state, or
customizing segmentation UI behavior, it belongs here before it belongs in `../../patches`.

## Entry Points

| File | Role |
|---|---|
| `src/index.ts` | OHIF extension descriptor. Exposes pre-registration, commands, panels, customizations, and utilities. |
| `src/preRegistration.ts` | Runtime setup before modes enter: tool registration, icon registration, measurement mappings, metadata providers, annotation stamping, viewport/session subscriptions. |
| `src/commandsModule.ts` | nnInteractive command surface: session lifecycle, inference, undo/reset, manual correction, SEG store/download overrides, segment jumping/toggling, payload generation. |
| `src/getPanelModule.tsx` | Exposes `aiToolBox` and `panelSegmentationWithTools`. |
| `src/getCustomizationModule.ts` | Registers segmentation stats header and Cornerstone overlay/tool customizations. |
| `src/getUtilityModule.ts` | Exposes utility modules used by other package code. |

## Main Folders

| Folder | Role |
|---|---|
| `src/panels/` | AI toolbox panel plus extension-owned segmentation panel/table fork. |
| `src/tools/` | nnInteractive prompt tool subclasses (`Probe2`, `RectangleROI2`, `PlanarFreehandROI2`, `PlanarFreehandROI3`). |
| `src/icons/` | Icons registered with `Icons.addIcon(...)` in `preRegistration.ts`. |
| `src/customizations/` | Components plugged into OHIF customization slots. |
| `src/utils/` | Shared runtime helpers: toolbox state, multipart parsing, measurement-state event dispatch. |

## Command Ownership

This extension intentionally overrides or supplements some stock OHIF commands. Keep related command
families together:

- session commands: `initNninter`, `nninterSessionStatus`, `closeNninterSession`
- inference commands: `nninter`, `undoNninter`, `resetNninter`, `resetSegment`
- manual correction: `applyNninterManualCorrection`, brush add/erase state
- UI bridge commands: `setAiToolActive`, `runAiSegmentation`
- navigation/visibility: `jumpToSegment`, `toggleCurrentSegment`
- SEG operations: store/download/generate behavior that must preserve nnInteractive metadata

Do not split store/download/generate changes across extension and source patches unless there is no
choice. These flows share assumptions about segmentation ids, display sets, and prompt metadata.

## Prompt Tool Ownership

Prompt tool behavior should live in `src/tools/promptTools.ts` when possible. The current subclasses
own stored-prompt reconstruction through `_addNewAnnotationFromIndex(...)`, and `commandsModule.ts`
owns fallback extraction of IJK prompt payloads from measurement geometry.

The remaining package-level prompt/rendering behavior in `../../node-module-patches` should only move
here after testing all prompt types:

- positive/negative point
- positive/negative box
- positive/negative scribble
- positive/negative lasso
- stored SEG prompt reload
- live mode

## Segmentation Table

`src/panels/SegmentationTable/` is a local fork of the relevant OHIF segmentation table pieces. This
is deliberate: the nnInteractive panel needs multi-select, generated stats controls, prompt cleanup,
and manual-correction ergonomics that are easier to reason about in an owned component tree.

When upstream OHIF changes its table, do not blindly copy the new version over this folder. First
check whether the change affects:

- visibility and measurement-state updates
- active segment selection
- generated bidirectional stats
- prompt cleanup when segments/segmentations are removed
- manual correction brush add/erase workflows

## Runtime Assumptions

- The backend proxy is reachable under `/nninteractive/infer/...`.
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
- undo/reset/next object
- store/export SEG
- reload stored SEG and see prompts reconstructed
- generated bidirectional/stat display
