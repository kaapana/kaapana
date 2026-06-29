# OHIF-AI source patches

These patches are applied (in filename order) with `git apply` to a **pristine** upstream
OHIF checkout at build time — see the parent `Dockerfile`. Together they reproduce the
CCI-Bonn/OHIF-AI fork's source delta vs pristine OHIF `d383be7c` (the additive nnInteractive
feature + its supporting in-place edits). They are split by concern so each piece can be
reviewed and re-validated independently when upgrading OHIF.

The combined result is byte-for-byte identical to the historical single `ohif-ai.patch`.

> **Why this document exists.** Every patch here edits OHIF's *own source files in place*
> (a true fork-by-overwrite), rather than adding functionality through OHIF's supported
> extension points. That works, but it makes every OHIF upgrade a manual re-validation of
> ~3,000 changed lines, and it lets bugs hide as diffs buried inside OHIF files (e.g. the
> DICOM-SEG `SegmentAlgorithmType` regression — a one-line corruption inside a 90-line
> in-place rewrite of `generateSegmentation`). This README documents, per patch, **why it
> exists, whether it is truly needed, and whether a cleaner "derive-and-extend" alternative
> exists** so the in-place residue can be shrunk over time. The audit was verified against the
> pristine upstream tree at `d383be7c` and the OHIF docs
> (<https://docs.ohif.org/platform/extensions/>, <https://docs.ohif.org/platform/modes/>).

---

## TL;DR — the big picture

`platform/app/pluginConfig.json` now registers `@kaapana/extension-nninteractive` and
`@kaapana/mode-nninteractive` beside the standard `@ohif/extension-*` packages. The historical fork
was delivered by patching built-in packages (`extension-default`, `extension-cornerstone`,
`extension-cornerstone-dicom-seg`, `platform/ui-next`, `platform/core`, `mode-longitudinal`) in
place; the current work is shrinking that in-place residue into the kaapana extension + mode.

The large majority of that delta is **purely additive** and could live in a dedicated extension +
custom mode, using OHIF mechanisms that already exist at this version:

| Patch | Concern | Truly needs a patch? | Clean home (future work) |
|---|---|---|---|
| `00-deps-build` | dep version pins, root `resolutions`, lerna, tailwind CSS, webpack/rsbuild guards | **Yes — build/deps** | Unavoidable (must match `../yarn.lock`). Only the 23-line scrollbar CSS could ship in an extension. |
| `10-nninteractive-app` | default study sort + right panel width residue | **Mostly extracted** | Commands, AI toolbox, `toolboxState`, and `multipart` now live in `@kaapana/extension-nninteractive`; only two OHIF default-layout/default-sort edits remain. |
| `20-nninteractive-cornerstone` | segmentation panel/table coupling + small core SEG/stat/jump fixes | **Mostly extracted** | Command overrides, prompt tools, measurement mappings, stats header customization, SEG overlay tools, prompt metadata stamping, and active-viewport init now live in `@kaapana/extension-nninteractive`; residue remains until the segmentation table is forked/upstreamed. |
| `30-nninteractive-ui` | prompt-tool icons, SegmentationTable/DataRow UI | **Partly** | Icons → `Icons.addIcon()` in `preRegistration`. SegmentationTable edits → **upstream PR** (no slot). |
| `40-platform-core` | hotkeys, MeasurementService visibility-on-load, MetadataProvider, ViewportGrid | **Partly** | Hotkeys → custom-mode `hotkeys`. `docker-nginx-orthanc.js` is **dead** → delete. Rest → **upstream PR**. |
| `50-mode` | `aiToolBox` toolbar section, prompt-tool buttons, tool groups | **Extracted — patch removed** | `@kaapana/mode-nninteractive` owns the layout, toolbar sections, prompt-tool buttons, tool groups, and now points at the kaapana panel composition. |
| `60-version-bump` | version strings | **No (cosmetic)** | Dockerfile `ARG`/`sed` instead of a tracked patch. |

### The target architecture ("derive and extend", not overwrite)

Introduce **two new packages, COPYed into the build and registered in `pluginConfig.json`** (the
Dockerfile already shows the seam — it `COPY`s `pluginConfig.json` and could `COPY` package dirs):

1. **`@kaapana/extension-nninteractive`**
   - `getCommandsModule` → the 12 `nninter*` commands (patch 10) **and** same-named overrides of
     `generateSegmentation` / `downloadSegmentation` / `storeSegmentation` (patch 20). *(Override all
     three together: `download`/`store` call `actions.generateSegmentation` directly, not via
     `commandsManager`.)*
   - `getPanelModule` → the AI Toolbox panel (patch 10's `isAIToolBox` branch) + the fork's
     `PanelSegmentation` (patch 20), so OHIF's `Toolbox.tsx`/`getPanelModule`/`PanelSegmentation`
     stay pristine.
   - `getUtilityModule` → `toolboxState`, `multipart` (patch 10).
   - `getCustomizationModule` → replace `panelSegmentation.customSegmentStatisticsHeader` (patch 20),
     extend `cornerstone.overlayViewportTools` (patch 20, currently *bypassed*).
   - `preRegistration` → `cornerstoneTools.addTool(Probe2Tool, …)`, `measurementService.addMapping(…)`
     for the prompt-tool mappings, `Icons.addIcon('tool-nninter', …)` (patch 30 icons),
     `measurementService` live-mode subscriptions, and a `viewportGridService`
     active-viewport subscription (replacing the `TrackedMeasurementsContext` edit).
2. **`@kaapana/mode-nninteractive`** — owns the `aiToolBox` toolbar sections, tool-group
   memberships, layout (`rightPanelClosed:false`), and declares the extension above as a dependency.
   This absorbs patch 50; patch 40's hotkeys are still a remaining migration target.

   *UX caveat:* the feature is meant to appear in the **default** workflow Kaapana already routes to.
   A separate mode adds a route/mode-selector step — preserve current UX by making it the default
   (only) mode in `pluginConfig.json`.

### What stays in-place — the **strict** lens (exact hooks only)

The verdicts in this README come in two flavors, because "extensionizable" depends on how strict you
are. The **strict** lens calls something extensionizable only when an exact OHIF hook reproduces its
behavior *identically*. Under that lens a small residue remains, most of it best fixed by
**upstreaming a hook to OHIF**:

- **`00-deps-build`** — dependency pins / `resolutions` / build config. Structural; must match
  `../yarn.lock`. *This is the patch most likely to break on an OHIF bump.*
- **`platform/ui-next` SegmentationTable family** (DataRow, SegmentationSegments, AddSegmentRow,
  context — patch 30): OHIF v3.10 exposes **no row-rendering customization slot**, so adding in-row
  buttons / checkboxes / measurement toggles requires editing `ui-next`. → **prime upstream PR**
  (add a `customDataRow` / row-action slot).
- **A handful of core bug-fixes / behavior hooks** with no extension seam (patch 20 & 40): the
  `MeasurementService` "hide on load when `toolLoad===true`" hook; `MetadataProvider` numeric
  pixel-spacing coercion; the `ViewportGrid` + `ViewportPane` hover-activate pair;
  `CustomizableViewportOverlay`'s unsorted-imageIds instance-number fix. → **upstream PR candidates**
  (several are genuine correctness fixes useful to everyone).
- **Two `SegmentationService` public methods** (patch 20) consumed by patch 30's UI — relocatable to
  a util/command if the UI is redirected, otherwise an in-place add.

### The **relaxed** lens: reimplement *beside* OHIF, don't edit *inside* it

If you relax "identical behavior" to **"functionally equivalent, may look/behave a little
differently,"** almost everything except `00-deps-build` can leave the in-place patches. The trick is
to run an equivalent path *beside* OHIF rather than editing OHIF's own path:

| Instead of editing OHIF's… | …ship your own equivalent | Delta you accept |
|---|---|---|
| shared component (SegmentationTable, overlay item) | your own component via `getPanelModule` / a `CustomizationService` slot | looks slightly different; a maintained fork that won't auto-inherit OHIF's UI fixes |
| inline hook in a service handler (`toolLoad` hide, `neg`/`manualCorrection` stamp) | a **parallel event listener** (`MEASUREMENT_ADDED` / `ANNOTATION_ADDED`) in `preRegistration` | possible 1-frame flicker / handler-ordering quirk |
| `MetadataProvider` internals (pixel-spacing coercion) | a **registered metadata provider** (`cornerstone.metaData.addProvider`, higher priority) | must confirm consumers read the provider chain |
| internal overlay helper (instance-number) | a **custom overlay item** via the `viewportOverlay` customization | none material |
| shared component styling (`SidePanel` scroll/color) | **CSS you ship** (the `.side-panel-scrollable` class already exists) | none material |
| a new service method | a **command or util** in your extension | callers must be redirected to it |
| a hardcoded default (panel width, study-browser sort, viewport activation) | a **config flag** (`activateViewportBeforeInteraction`) or a runtime apply on `DISPLAY_SETS_CHANGED` (patch 10 already does the sort this way) | none material |

Under the relaxed lens the irreducible residue collapses to essentially **just `00-deps-build`** (plus
anything you *choose* to keep in-place). The per-file tables below carry a **"Relaxed-equivalent"**
column showing where each strict-residue item moves.

**Rule of thumb for which lens to apply:**
- **Large additive / UI chunks** (most of 10, 20, 30, 50) and anything you'd fork anyway → the
  **relaxed extension** is the clear win: OHIF upgrades stop conflicting *in OHIF's tree*.
- **Tiny core correctness one-liners** (`MetadataProvider`, the overlay instance-number, the
  `ViewportGrid` stale-closure) → a 2-line in-place patch is fine, and these are genuine bugs that
  belong **upstream** anyway; owning a whole custom provider/overlay to change one value is more code
  for little gain.
- **Behavioral deltas are real:** the parallel-listener approaches can flicker or reorder — verify in
  the viewer before adopting.

---

## Per-patch detail

### `00-deps-build.patch` — BUILD/DEPS · unavoidable

**Goal.** Make dependency resolution reproduce the fork's pinned tree so `../yarn.lock` and
`../node-module-patches/` (Cornerstone 3.33.5 / vtk 32.12.0) apply cleanly.

**What it does.** Mechanical `@ohif/* 3.10.2 → 3.10.4` bump across ~25 `package.json` + `lerna.json`
(keeps workspace peers self-consistent); real pins — `@cornerstonejs/* ^3.11.7`, `dcmjs 0.42.0`,
`webpack 5.104.1`, `webpack-dev-server 5.2.1`, `swiper ^12`, `lucide-react ^0.394`; a root
`resolutions` block (+27 entries — mostly CVE/transitive hygiene, plus `axios`/`protobufjs` used by
the nnInteractive client); workspace edits (`packageManager: yarn@1.22.22`, remove `platform/cli`,
`--skip-nx-cache`); 23 lines of `.side-panel-scrollable` CSS in `tailwind.css`; and `existsSync`
guards around `commit.txt` reads in `rsbuild.config.ts` / `.webpack/webpack.base.js`.

**Needed?** Yes. Versions, `resolutions`, lerna and the workspace/script edits are build-level and
cannot be expressed as an extension. The only non-build content is the scrollbar CSS (could ship in
an extension's stylesheet — negligible payoff). The `commit.txt` guards could be replaced by a
`touch commit.txt` in the Dockerfile.

**Future work.** Keep as-is. **Re-validate against `../yarn.lock` on every OHIF bump** — the
`resolutions` block in particular will drift with upstream and CVE advisories.

### `10-nninteractive-app.patch` — mostly extracted; tiny residue

**Goal.** Historically this added the nnInteractive *behavior* (commands), the *panel UI* (AI
Toolbox), and two helper modules in `extensions/default`. Those additive parts now live in
`@kaapana/extension-nninteractive`; this patch only carries the two remaining default-UI tweaks.

**What it does.**
- `PanelStudyBrowser.tsx` (+14): default series sort on load. Kaapana residue: OHIF v3.10 has no
  extension hook for the default study-browser sort.
- `panels.ts` (+3/−2): wider right panel. Kaapana residue: OHIF v3.10 keeps default panel widths in
  layout constants.

**Moved out of this patch.**
- `packages/extension-nninteractive/src/commandsModule.ts`: 12 nnInteractive commands — session
  lifecycle (`initNninter`, `nninterSessionStatus`, `closeNninterSession`), the core `nninter`
  inference call, `undoNninter`/`resetNninter`/`resetSegment`,
  `applyNninterManualCorrection`, `setAiToolActive`/`runAiSegmentation`,
  `jumpToSegment`/`toggleCurrentSegment`, plus the live-mode measurement subscriptions.
- `packages/extension-nninteractive/src/panels/NnInteractivePanel.tsx`: the AI toolbox UI, hotkeys,
  availability/session polling, prompt tools, manual correction controls, and export button.
- `packages/extension-nninteractive/src/utils/toolboxState.ts` and `src/utils/multipart.ts`: the
  module-singleton UI-state store and multipart/gzip response parser.
- `packages/extension-nninteractive/src/getPanelModule.tsx`: exposes both `aiToolBox` and a
  `panelSegmentationWithTools` composition that renders the extension-owned AI toolbox before the
  cornerstone segmentation panel.
- `packages/mode-nninteractive/src/index.ts`: now selects
  `@kaapana/extension-nninteractive.panelModule.panelSegmentationWithTools`.

**Needed as a patch?** Only the two small residue hunks remain. Both are unrelated to nnInteractive
proper and are **upstream-PR candidates** unless OHIF gains a mode/config hook for default
study-browser sorting and panel widths.

### `20-nninteractive-cornerstone.patch` — mostly extracted; panel/core residue

Integration glue into `extension-cornerstone` + `extension-cornerstone-dicom-seg`. Per-file verdict:

| File | Strict verdict | Clean home | Relaxed-equivalent |
|---|---|---|---|
| `customizations/CustomSegmentStatisticsHeader.tsx` | **EXTRACTED** | `packages/extension-nninteractive/src/customizations/CustomSegmentStatisticsHeader.tsx` registered by `getCustomizationModule`. | — |
| `cornerstone-dicom-seg/.../initSEGToolGroup.ts` | **EXTRACTED** | restored upstream hook; `getCustomizationModule` provides `cornerstone.overlayViewportTools`. | — |
| `measurementServiceMappingsFactory.ts`, `constants/supportedTools.js`, `initMeasurementService.ts` (mappings) | **EXTRACTED** | prompt tool aliases are registered with `measurementService.addMapping(…)` in `preRegistration`. | — |
| `initCornerstoneTools.js` | **EXTRACTED** | prompt tool subclasses are registered with `cornerstoneTools.addTool(…)` in `preRegistration`; the mode uses literal tool names instead of patched `toolNames.*` exports. | — |
| `extensions/cornerstone/commandsModule.ts`, `cornerstone-dicom-seg/commandsModule.ts` | **MOSTLY EXTRACTED** | command overrides live in `packages/extension-nninteractive/src/commandsModule.ts`; one tiny core residue keeps measurement metadata pointed at the stored SEG display set after `createReportAsync`. | move with a forked panel/store flow later |
| `getPanelModule.tsx`, `panels/PanelSegmentation.tsx` | **PARTLY BRIDGED** | the mode now uses `@kaapana/extension-nninteractive.panelModule.panelSegmentationWithTools`, which composes the extracted AI toolbox with the existing cornerstone segmentation panel. | next step: own panel + own table/row components → drops the patch-30 dependency entirely |
| `Viewport/OHIFCornerstoneViewport.tsx` | **NO-OP — ✅ removed** | hunk deleted. | — |
| `services/SegmentationService/SegmentationService.ts` | **IRREDUCIBLE (strict)** | 2 public methods used by patch 30 + a numeric-center STACK jump path. (dead `MEASUREMENT_VISIBILITY_CHANGED` **✅ removed**.) | **commands/utils** in the extension; redirect patch-30 UI to call them |
| `initMeasurementService.ts` (metadata stamp) | **EXTRACTED** | `preRegistration` registers a parallel `ANNOTATION_ADDED` listener that stamps `metadata.neg`/`manualCorrection`. | verify ordering in browser; move into a forked prompt-tool adapter if needed |
| `ViewportSegmentationMenu.tsx`, `updateSegmentationStats.ts` (cm³), `CustomizableViewportOverlay.tsx`, `OHIFCornerstoneSEGViewport.tsx`, `TrackedMeasurementsContext.tsx` | **small in-place / upstream-PR** | mostly bug-fixes → upstream; `TrackedMeasurementsContext` is now replaced by a `viewportGridService` subscription in `preRegistration`. | overlay → **custom overlay item**; cm³ → **own stats component**; SEG spacing → **custom metadata provider** |

**Why command-override beats in-place rewrite:** the recently-fixed `SegmentAlgorithmName = seriesInstanceUid`
bug lived buried inside this patch's 90-line in-place `generateSegmentation` rewrite. As an
extension command-override it is now a self-contained, reviewable unit. Remaining effort is the
`ui-next` segmentation table coupling and the handful of small upstream-style fixes above.

### `30-nninteractive-ui.patch` — moderate-to-high; icons are a clean win

**Goal.** Render the prompt-tool icons and the per-segment/multi-select SegmentationTable UI that
patch 20's `PanelSegmentation` feeds.

| File(s) | Strict verdict | Clean home | Relaxed-equivalent |
|---|---|---|---|
| 4 NEW `Icons/Sources/Tool*.tsx` + `Icons.tsx` (+12) + `Tools.tsx` (+3) | **Extracted — patch removed** | `packages/extension-nninteractive/src/preRegistration.ts` registers the icons with `Icons.addIcon(name, component)`. | — already clean |
| `StudyBrowserSort.tsx` (+2/−1) | **CONFIG/redundant** | already applied at runtime by patch 10; likely removable. | — already clean |
| `SegmentStatistics.tsx` (+1/−1) | **upstream/customization** | hides the `bidirectional` stat — no stat-filter hook. | **own stats component** in the fork's panel |
| `DataRow.tsx`, `SegmentationSegments.tsx`, `AddSegmentRow.tsx`, `SegmentationTableContext.tsx` | **UPSTREAM-PR (irreducible, strict)** | no row-rendering slot in v3.10 — **upstream PR: add a `customDataRow`/row-action slot.** | **fork the table as your own `getPanelModule` components** (registered, not in-place) — accept UI drift |
| `SidePanel.tsx` (+10), `ViewportPane.tsx` (+1) | **upstream-PR** | scrollable panel; hover-to-activate (pairs w/ patch-40 `ViewportGrid`). | `SidePanel` → **shipped CSS**; `ViewportPane` → **config** (`activateViewportBeforeInteraction`) / viewport wrapper |

**Quality flags (fix regardless of patch-vs-extension):** `SegmentationSegments.tsx` uses a **500 ms
`setInterval` poll** (on top of a live `document` `measurement-state-changed` listener) to re-render,
and reaches into `servicesManager` directly from a shared presentational component — it should
receive visibility via context and rely solely on the `measurement-state-changed` signal (now fired
from the extracted `commandsModule.ts`), fired at *every* visibility-change site, instead of
polling. *(Needs a UI test — see "remaining" in the sequencing section.)* `SidePanel.tsx` hardcodes
`backgroundColor:'#090c29'` (use a theme token).

### `40-platform-core.patch` — high for the bulk, small residue

| File | Strict verdict | Clean home | Relaxed-equivalent |
|---|---|---|---|
| `platform/app/public/config/docker-nginx-orthanc.js` (+12) | **DEAD — ✅ removed** | never loaded (kaapana uses `kaapana.js`); hunk deleted. | — |
| `core/src/defaults/hotkeyBindings.ts` (+22/−10) | **CUSTOM-MODE** | a mode supplies its own `hotkeys` array — move it there; the core edit vanishes. | — already clean |
| `core/.../MeasurementService.ts` (+13) | **IRREDUCIBLE (strict)** | "hide on load when `metadata.toolLoad===true`"; no create-time hook (`toggleVisibilityMeasurement`/`Many`/`isVisible` are stock). *(block is correctly braced, just untidy; inner guard redundant.)* | **`MEASUREMENT_ADDED` subscriber** in `preRegistration` — accept a possible 1-frame flicker |
| `core/src/classes/MetadataProvider.ts` (+2/−2) | **upstream-PR** | numeric pixel-spacing coercion (correctness fix). | **custom metadata provider** (`metaData.addProvider`) — verify consumers read the chain |
| `platform/app/.../ViewportGrid.tsx` (+9/−1) | **upstream-PR** | live active-viewport read (stale-closure fix); pairs w/ `ViewportPane`. | partly **config** (`activateViewportBeforeInteraction`); else keep as a small upstream-bound patch |

### `50-mode.patch` — ✅ extracted into `@kaapana/mode-nninteractive`

**Goal.** Wire the feature into the longitudinal workflow: swap to `panelSegmentationWithTools`,
open the right panel by default, and (in `onModeEnter`) `createButtonSection(…)` for the `aiToolBox`
sections; add tool-group memberships (`initToolGroups.js`) and ~483 lines of button definitions
(`toolbarButtons.ts`).

**Needed as a patch?** No — toolbar sections, `onModeEnter` tool-group setup, and layout are exactly
what a **custom mode** owns. This patch has been removed. Its patched `initToolGroups.js`,
`toolbarButtons.ts`, and longitudinal layout changes now live in `packages/mode-nninteractive/`,
which the Dockerfile copies to `/src/modes/nninteractive` before `yarn install`.

**Current bridge.** The mode now references
`@kaapana/extension-nninteractive.panelModule.panelSegmentationWithTools`. That kaapana panel
composition owns the AI toolbox and delegates the segmentation table to the still-patched
`@ohif/extension-cornerstone.panelModule.panelSegmentation`. The next extraction target is therefore
patch 20/30's segmentation panel/table coupling.

**UX tradeoff.** Editing `longitudinal` directly is a deliberate *delivery* choice: the tools must
appear in the default viewer Kaapana routes to, not behind a new mode tile. Preserve that by making
the custom mode the default in `pluginConfig.json` (or accept one extra selection step). Effort:
**low** for the mode shell; **medium-high** for the full extension+mode refactor.

### `60-version-bump.patch` — cosmetic

`version.json`/`version.txt` strings shown in the viewer's About info (the commit hash duplicates the
Dockerfile's `OHIF_COMMIT`; the `version.txt` hunk is effectively a no-op). Could be a Dockerfile
`ARG`/`sed` step instead of a tracked patch. Low priority.

---

## Recommended sequencing (future work)

1. **Quick wins, no upstream needed.** ✅ *Done:* deleted the dead `docker-nginx-orthanc.js` hunk,
   the no-op `OHIFCornerstoneViewport.tsx` comment, and the dead `MEASUREMENT_VISIBILITY_CHANGED`
   service event. *Remaining (needs a UI test):* replace the `SegmentationSegments` 500 ms poll with
   the already-live `measurement-state-changed` signal, ensuring it is dispatched at every
   visibility-change site (single toggle, bulk `onTogglePromptsVisibility`, initial `toolLoad` hide,
   deletion).
2. **Scaffold `extension-nninteractive`** and move the additive bulk: commands (10, 20),
   utilities + AI panel (10), icons via `addIcon` (30), measurement mappings + `addTool` +
   customization overrides `CustomSegmentStatisticsHeader` / `overlayViewportTools` (20). Register in
   `pluginConfig.json`; `COPY` the package in the Dockerfile.
3. **Scaffold `mode-nninteractive`** for toolbar sections, tool groups, and layout. ✅ *Done for
   patch 50:* the package is copied into the OHIF workspace and registered as the default mode.
   *Remaining:* move patch-40 hotkeys into the mode.
4. **Close the strict-residue gaps — two options.** Either **upstream PRs** for the genuine hooks (a
   SegmentationTable row/action slot — unblocks patch 30 + the fork's `PanelSegmentation`; a
   study-browser default-sort + panel-width customization; an "initial measurement visibility" hook;
   and the `CustomizableViewportOverlay` / `MetadataProvider` / `ViewportGrid` correctness fixes);
   **or** apply the **relaxed-equivalent** reimplementations now (own table components, parallel event
   listeners, a custom metadata provider, a custom overlay item, shipped CSS, config flags) to avoid
   waiting on upstream — accepting the UI-drift / flicker tradeoffs noted in the relaxed-lens section.
   Heuristic: tiny correctness one-liners → upstream; large UI chunks → relaxed extension.
5. **Residue that stays a patch under *either* lens:** `00-deps-build` (and `../node-module-patches/`).

---

## Upgrading OHIF

Bump `OHIF_COMMIT` in the `Dockerfile`, then re-validate each patch applies (regenerate the
hunks for any whose target files upstream moved). The dependency layer (`00`) must stay in
sync with `../yarn.lock` and the `../node-module-patches/` Cornerstone/vtk patches (currently 3.33.5 / 32.12.0).

Every in-place patch above is a re-validation cost on each upgrade; the smaller the in-place residue
(see "future work"), the cheaper the next bump.
