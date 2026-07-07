# Node module patches

These patches are applied with `patch-package` after `yarn install` in the OHIF viewer Docker build.
They are different from `patches/*.patch`: those edit the fetched OHIF source tree, while these edit
installed npm packages at their pinned versions.

The current pins are enforced by the Dockerfile before patching:

| Package | Patched version | Why version-pinned |
|---|---:|---|
| `@cornerstonejs/core` | `3.33.5` | `VoxelManager` internals changed across Cornerstone releases. |
| `@cornerstonejs/tools` | `3.33.5` | Segmentation rendering, prompt tools, and worker/stat internals changed across Cornerstone releases. |
| `@kitware/vtk.js` | `32.12.0` | Marching-squares output coordinates changed/need validation with Cornerstone's worker conversion path. |

## Rule of Thumb

- **Keep as node-module patch** when the behavior is a low-level Cornerstone/vtk runtime fix with no
  public extension hook: labelmap cache-to-VTK sync, duplicate labelmap actors, VoxelManager scalar
  data access, worker geometry, marching-squares coordinate space.
- **Move to `@kaapana/extension-nninteractive`** when the behavior is nnInteractive feature logic:
  prompt-annotation metadata/stamping, prompt payload extraction from annotation geometry, prompt
  visibility/coloring.
- **Upstream candidate** when the patch is a general correctness fix useful beyond nnInteractive.

## Current State

Prompt-tool feature code lives in the extension:

- `packages/extension-nninteractive/src/tools/promptTools.ts` owns the `Probe2`,
  `RectangleROI2`, `PlanarFreehandROI2`, and `PlanarFreehandROI3` subclasses, which provide
  `_addNewAnnotationFromIndex(...)`.
- `packages/extension-nninteractive/src/model/coordinateMapping.ts` derives prompt payloads from
  each annotation's geometry.

The labelmap, VoxelManager, vtk, and worker fixes below stay as node-module patches.

## Patch Inventory

### `@cornerstonejs+core+3.33.5.patch`

| File | What it changes | Needed for nnInteractive? | Move? |
|---|---|---|---|
| `utilities/VoxelManager.js` | Finds the first cached image voxel manager instead of assuming image index `0` is cached; exposes `getImageIds()` and maps derived labelmap imageIds back to referenced imageIds; computes complete scalar length from a cached slice. | **Yes.** nnInteractive writes/reads derived labelmap images and SEG/export/stat flows depend on reliable scalar arrays and referenced image ids. | **Keep as node-module patch** until Cornerstone exposes/ships equivalent behavior. This is a low-level data structure fix, not extension logic. |

Tradeoff: keeping it is version-sensitive, but moving it to extension code would require monkey-patching
Cornerstone internals at runtime, which is harder to reason about than `patch-package`.

### `@kitware+vtk.js+32.12.0.patch`

| File | What it changes | Needed for nnInteractive? | Move? |
|---|---|---|---|
| `Filters/General/ImageMarchingSquares.js` | Emits IJK coordinates instead of world coordinates because `computeWorker.js` performs the world conversion with the direction matrix later; removes console timers. | **Likely yes** for correct contour/bidirectional geometry on non-identity direction matrices. | **Keep as node-module patch** or upstream. The coordinate-space fix belongs in vtk/Cornerstone integration, not the extension. |

Tradeoff: this is a tiny patch with high geometry impact. The timer removal is cosmetic, but keeping it
bundled with the coordinate fix is harmless.

### `@cornerstonejs+tools+3.33.5.patch`

This is the large mixed patch. It should be treated as several smaller logical patches:

| Area | Files | What it does | Needed? | Best home |
|---|---|---|---|---|
| Cursor visibility | `cursors/elementCursor.js`, `planarFreehandROITool/drawLoop.js` | Prevents Cornerstone from hiding/resetting the cursor while drawing. | **Maybe.** Cosmetic/UX; not core nnInteractive logic. | Test-removable. If kept, prefer a tool/subclass option later. |
| Stack labelmap update | `eventListeners/segmentation/labelmap/performStackLabelmapUpdate.js` | Resolves labelmap image by `actorEntry.referencedId` instead of positional indexing, avoiding undefined cache lookups and missed render updates. | **Yes.** This protects stack labelmap repaint/update after nnInteractive writes pixels. | Keep patch / upstream. |
| Prompt rehydration from stored SEG | `stateManagement/segmentation/SegmentationRenderingEngine.js` | Reads JSON prompt metadata from `SegmentDescription`, calls `Probe2`/`RectangleROI2`/freehand `_addNewAnnotationFromIndex`, and marks rehydrated annotations selected. | **Yes for stored-SEG prompt restore**, but it is feature logic. | **Move next** into the extension via segmentation/viewport subscriptions. It remains patched for now because it is tied to the moment labelmap actors are available. |
| Render queue behavior | `SegmentationRenderingEngine.js` | Removes the pending render queue and coalesces render requests into the current animation frame set. | **Probably yes** for avoiding stale/lagged segmentation renders, but needs isolation. | Keep patch until tested separately; upstream candidate if generally useful. |
| Clear segment value | `helpers/clearSegmentValue.js` | Uses scalar array mapping/setScalarData to clear a segment. | **Maybe.** There is already extension code for segment reset; this may support stock segmentation UI paths. | Test-removable after reset/delete workflows are covered. |
| Prompt base-tool cached stats | `ProbeTool.js`, `RectangleROITool.js`, `PlanarFreehandROITool.js`, `drawLoop.js`, `renderMethods.js`, `AnnotationTool.js` | Stores prompt payloads (`index`, `pointsInShape`, `boundary`, `scribble`), hides prompt text boxes, colors negative prompts, supports tiny scribbles/open-vs-closed behavior and slice-index corrections. | **Partly.** Payload extraction now has extension fallbacks, but these hunks still affect live drawing behavior and prompt display. | **Move gradually** into extension-owned subclasses. `_addNewAnnotationFromIndex` has already moved. Remaining stats/render changes need A/B tests for point, box, scribble, lasso, and live mode. |
| Labelmap add/render/remove | `Labelmap/addLabelmapToElement.js`, `Labelmap/labelmapDisplay.js`, `Labelmap/removeLabelmapFromElement.js` | Gives stack labelmap actors stable per-image representation UIDs, suppresses recursive modification events when actors already exist, copies cache scalar data into VTK before marking render dirty, and removes all actors for a segmentation. | **Yes.** This is the core "mask updates actually show up" path after nnInteractive writes labelmap pixels. | Keep patch / upstream. Extension code can work around some cases manually, but the renderer fix belongs in Cornerstone tools. |
| Bidirectional/stat geometry | `findLargestBidirectional.js`, `getOrCreateImageVolume.js`, `getSegmentLargestBidirectional.js`, `computeWorker.js` | Carries slice index through worker results, converts IJK/world consistently, handles segment index typing, avoids empty image volumes, and changes major/minor-axis search. | **Yes** for robust generated bidirectional stats and SEG-derived stats. | Keep patch / upstream unless replacing the whole stats path in the extension. |

## What Already Moved

The most clearly extension-owned helper moved out of the package patch:

| Previously patched into | Now lives in | Why |
|---|---|---|
| `ProbeTool._addNewAnnotationFromIndex` | `Probe2Tool` in `extension-nninteractive/src/tools/promptTools.ts` | Only nnInteractive prompt reload needs it. |
| `RectangleROITool._addNewAnnotationFromIndex` | `RectangleROI2Tool` in `extension-nninteractive/src/tools/promptTools.ts` | Only nnInteractive prompt reload needs it. |
| `PlanarFreehandROITool._addNewAnnotationFromIndex` | `PlanarFreehandROI2Tool` / `PlanarFreehandROI3Tool` in `extension-nninteractive/src/tools/promptTools.ts` | Only nnInteractive prompt reload needs it. |
| Prompt payload extraction | `model/coordinateMapping.ts` | The extension turns prompt annotations into nnInteractive request payloads from annotation geometry. |

## Recommended Next Moves

1. **Keep all three node-module patch files for the current milestone.** They are part of the tested
   working state and contain real low-level fixes.
2. **Move prompt rehydration out of `SegmentationRenderingEngine.js`.** Best target:
   `extension-nninteractive` pre-registration/subscriber code that waits until the SEG display set and
   viewport tool group are ready, then creates prompt annotations through the extension prompt tools.
3. **Move remaining prompt display/stat behavior into subclasses.** This includes hidden text boxes,
   negative prompt color, tiny scribble behavior, and closed/open freehand stats. Do this with one
   browser smoke test per prompt type.
4. **Leave labelmap/VoxelManager/vtk/worker fixes as node-module patches** unless upstreamed. These
   are not clean extension responsibilities.
5. **After each removal bucket, build and test:** point/box/scribble/lasso prompts, negative prompts,
   manual correction brush add/erase, live mode, store/export SEG, reload stored SEG, and generated
   bidirectional stats.

## Upgrade Notes

On a Cornerstone/vtk version bump, do not blindly carry these patches forward. First check whether the
upstream package already contains the same fix. If not, reapply only the low-level runtime fixes and
keep nnInteractive feature behavior in `extension-nninteractive` wherever possible.
