# @kaapana/extension-nninteractive

Kaapana OHIF extension for the nnInteractive segmentation workflow.

## Entry Points

| File | Role |
|---|---|
| `src/index.ts` | OHIF extension descriptor. Exposes pre-registration, commands, and the panel. |
| `src/preRegistration.ts` | Runtime setup before modes enter: prompt-tool and icon registration, prompt-annotation stamping (and live-mode submit), the 3D-focus guard, and the console debug hooks. |
| `src/commandsModule.ts` | Thin nnInteractive command surface over the `model/` layer: session lifecycle, inference, undo/reset, manual correction, SEG store/download (all objects → one overlapping SEG, with a series-name prompt on store), jumping to an object; also the viewport guard and the SEG import-split hook. |
| `src/model/` | Product logic split by concern: `sessionModel`, `imageModel`, `objectModel`, `promptModel`/`promptDisplay`, `coordinateMapping`, `segmentationBridge` (the only module touching labelmap voxels; objects packed into layer segmentations + import-split), `serverApi`, `store`, `types`. |
| `src/getPanelModule.tsx` | Exposes the single nnInteractive panel (`panelSegmentationWithTools`). |

## Main Folders

| Folder | Role |
|---|---|
| `src/panels/` | The nnInteractive panel (`NnInteractivePanel`) and its object list (`ObjectList`). |
| `src/tools/` | nnInteractive prompt tool subclasses (`Probe2`, `RectangleROI2`, `PlanarFreehandROI2`, `PlanarFreehandROI3`). |
| `src/icons/` | Icons registered with `Icons.addIcon(...)` in `preRegistration.ts`. |
| `src/utils/` | Shared runtime helpers: toolbox (UI) state and multipart response parsing. |

## Data Model & Workflow

**Prompts are locked Cornerstone annotations.** Each point/box/lasso/scribble is an annotation drawn
with one of the `Probe2`/`RectangleROI2`/`PlanarFreehandROI2`/`PlanarFreehandROI3` tools. `promptModel`
keeps a ledger of each prompt's positive/negative sign and submitted state; `preRegistration.ts`
stamps a prompt on draw and, in live mode, submits it on completion. `model/coordinateMapping.ts`
converts each annotation's geometry into the IJK payload the proxy expects, for both stack and MPR
planes.

**Objects are segments packed into layer segmentations.** Each object owns one segment index in an
ordinary single-labelmap OHIF segmentation (a "layer"); its voxels hold that index. Objects of one
layer cannot share voxels, so an object whose mask would overlap another object of its layer moves
to a layer where it fits (or a new one). A typical session needs one layer, so memory grows with
the number of overlapping objects, not with the number of objects. `model/segmentationBridge.ts` is
the only module that reads or writes labelmap voxels. The stack labelmap images are the single voxel store: Cornerstone 5 renders
them in stack viewports and, through an image-backed geometry volume, in MPR viewports, so a write
(or a brush stroke in either view) shows everywhere after `triggerSegmentationDataModified`. The
bridge also assigns each object a palette color, keeps every layer's representation in every
stack/MPR viewport (never in 3D), and locks all objects but the active one so the brush cannot paint
over a neighbour in the same layer.

**Session & inference.** `sessionModel` owns the backend session lifecycle over the `serverApi`
facade; `objectModel` tracks the active object and its dirty state. Running the prompts sends them
through the proxy, which returns a cropped mask that `segmentationBridge` writes into the active
object. Manual brush edits mark the object dirty and are sent back to the backend as `set_mask` on
the next run.

**Import / export.** On load, a stored SEG that OHIF hydrates as one multi-segment segmentation is
split into objects, preserving each segment's label and color. On store/download, all objects of
the series are merged into one overlapping DICOM SEG; store prompts for a series name first.

## Command Ownership

The extension's commands use their own names and never override stock OHIF commands, so other modes
are unaffected. Its global listeners (prompt annotations, viewport guard, SEG import-split, 3D focus
guard) act only while the nnInteractive mode is active: the mode calls `enterNninterMode` and
`exitNninterMode`, and exit closes the backend session. Keep related command families together:

- mode lifecycle: `enterNninterMode`, `exitNninterMode`
- session commands: `nninterSessionStatus` (heartbeat), `closeNninterSession`; the first prompt starts the session, and a run that finds its backend session gone (409) re-initializes once and re-seeds the object from the local mask
- inference commands: `nninter` (run prompts), `undoNninter`, `resetSegment`, `deleteNninterObject`
- object commands: `armNextNninterObject`, `loadSegmentForRefinement`
- manual correction: brush add/erase in manual-correction mode; edits mark the active object dirty and go to the backend as `set_mask` on the next run
- navigation: `jumpToSegment`
- SEG operations: `storeNninterSegmentation` and `downloadNninterSegmentation` merge all objects into one overlapping DICOM SEG

Do not split store/download changes across extension and source patches unless there is no choice.
These flows share assumptions about segmentation ids, display sets, and the layer labelmap layout.

## Prompt Tool Ownership

`src/tools/promptTools.ts` defines the prompt tools as renamed subclasses of the stock Cornerstone
tools, so prompts never mix with measurements. `model/promptDisplay.ts` styles them (pending vs.
committed, positive vs. negative) and locks submitted ones; `model/coordinateMapping.ts` converts each
prompt annotation's geometry into the IJK payload the proxy expects. There are no Cornerstone package
patches.

## Panel

`src/panels/NnInteractivePanel.tsx` is the mode's only right-hand panel and follows the workflow top
to bottom: prompt sign (positive/negative) → tool (point, box, scribble, lasso, correction brush) →
run options → objects → save. Each action has exactly one control, and its keyboard shortcut is
printed on that control; the panel's key handler is the single place those shortcuts are bound.
The backend session starts on the first prompt (there is no Initialize button); the header shows its
status. Reset and Delete ask for confirmation because they cannot be undone.

`src/panels/ObjectList.tsx` lists every object (one row per segment of the layer segmentations, in
creation order). Clicking a row selects the object for refinement and
jumps to it; visibility applies to every viewport showing it (MPR has three).

When changing the panel, keep:

- one control per action, with the shortcut on it
- single-step nnInteractive undo; the backend can undo only the latest interaction
- per-tab nnInteractive session ids; one user's close request must not close another user's lease

## Debugging

In the browser console, `__nnInteractiveDbg()` logs a snapshot of the session, active object, prompts
and every viewport's segmentation representations; `__nnInteractiveGpu.info()` reports the WebGL
capabilities that decide whether MPR volumes render.

## Runtime Assumptions

- The backend proxy is reachable under `/nninteractive/infer/...`, or `/project/<id>/nninteractive/...`
  when OHIF runs under `/project/<id>/`.
- The proxy keys sessions by study, series, and the OHIF tab's `clientSessionID`.
- The mode registers the prompt tools in the active tool groups.
- Stock OHIF 3.13 / Cornerstone 5: no OHIF source or node-module patches beyond Kaapana's shared
  `files/customization.patch`. Viewport activation is OHIF's default (click activates first).

## Smoke Test After Changes

Verify:

- the first prompt starts the session; leaving the mode closes it
- add all prompt types
- negative prompts subtract instead of add
- run segmentation and see mask update
- manual correction brush add/erase
- single-step undo/reset/next object
- store/export SEG (a series-name prompt appears before storing)
- reload stored SEG and see it split into objects
- object list: select (jumps to the object), hide/show, rename, color, delete
