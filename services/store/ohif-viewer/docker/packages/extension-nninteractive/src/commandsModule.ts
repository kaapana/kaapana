// Thin command layer. Every command delegates to a small model module — the command
// module owns no data model, no server bookkeeping, and no viewport internals.

import dcmjs from 'dcmjs';
import { cache, eventTarget, metaData } from '@cornerstonejs/core';
import { Enums as csToolsEnums } from '@cornerstonejs/tools';
import { adaptersSEG, helpers } from '@cornerstonejs/adapters';
import { DicomMetadataStore } from '@ohif/core';
import { createReportDialogPrompt } from '@ohif/extension-default';
// Not re-exported from the package index; this extension is built next to OHIF's default
// extension, so the relative path resolves at build time.
import PROMPT_RESPONSES from '../../default/src/utils/_shared/PROMPT_RESPONSES';

import * as sessionModel from './model/sessionModel';
import * as serverApi from './model/serverApi';
import * as objectModel from './model/objectModel';
import * as promptModel from './model/promptModel';
import * as imageModel from './model/imageModel';
import * as coord from './model/coordinateMapping';
import * as bridge from './model/segmentationBridge';
import { ObjectRef, PromptArrays, PromptKind, SourceImage, emptyPromptArrays } from './model/types';
import { toolboxState } from './utils/toolboxState';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;
const {
  Cornerstone3D: {
    Segmentation: { generateSegmentation },
  },
} = adaptersSEG;
const { downloadDICOMData } = helpers;

const TISSUE_CODE = { CodeValue: 'T-D0050', CodingSchemeDesignator: 'SRT', CodeMeaning: 'Tissue' };

/** How each prompt kind is converted to source voxels and which payload field it fills. */
const PROMPT_CONVERSION: Record<
  PromptKind,
  { toVoxels: (viewport: any, annotation: any, imageIds: string[]) => any; field: string }
> = {
  point: { toVoxels: coord.pointIJK, field: 'points' },
  box: { toVoxels: coord.boxIJK, field: 'boxes' },
  lasso: { toVoxels: coord.freehandIJK, field: 'lassos' },
  scribble: { toVoxels: coord.freehandIJK, field: 'scribbles' },
};

// Guard so the MPR/brush event subscriptions are installed only once, even if
// getCommandsModule is ever invoked more than once.
let subscriptionsInstalled = false;

const commandsModule = ({ servicesManager, commandsManager, extensionManager }: any) => {
  const {
    viewportGridService,
    cornerstoneViewportService,
    segmentationService,
    uiNotificationService,
    displaySetService,
  } = servicesManager.services;

  const notify = (message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') =>
    uiNotificationService.show({ title: 'nnInteractive', message, type });

  const activeViewport = () => {
    const id = viewportGridService.getActiveViewportId();
    return id ? cornerstoneViewportService.getCornerstoneViewport(id) : undefined;
  };

  // Resolve the source image series for a segmentation from its OWN referenced images (so a SEG
  // imported into a multi-series study splits onto the right series regardless of which viewport
  // is active), falling back to the active viewport's source.
  const sourceForSegmentation = (segmentationId: string): SourceImage | null => {
    const seg = segmentationService.getSegmentation(segmentationId);
    const firstRef = seg?.representationData?.[LABELMAP]?.referencedImageIds?.[0];
    const instance = firstRef ? metaData.get('instance', firstRef) : null;
    const displaySet = instance?.SOPInstanceUID
      ? displaySetService.getDisplaySetForSOPInstanceUID(
          instance.SOPInstanceUID,
          instance.SeriesInstanceUID
        )
      : null;
    const source = displaySet?.imageIds?.length ? imageModel.toSourceImage(displaySet) : null;
    return source ?? imageModel.getActiveSource(servicesManager);
  };

  // ── Session ──────────────────────────────────────────────────────────────────────────────

  /** The ready session for the displayed series, starting one if needed. */
  async function ensureSession(): Promise<SourceImage | null> {
    if (
      !sessionModel.isReadyForActive(servicesManager) &&
      !(await sessionModel.initialize(servicesManager))
    ) {
      notify('Could not start an nnInteractive session for this series.', 'warning');
      return null;
    }
    return sessionModel.getSource();
  }

  function handleServerError(error: any, prompts?: any[]) {
    if (serverApi.isSessionExpiredError(error)) {
      sessionModel.markExpired();
      notify('nnInteractive session expired. Please re-initialize.', 'warning');
    } else {
      notify(`nnInteractive request failed: ${error?.message ?? error}`, 'error');
    }
    if (prompts?.length) {
      promptModel.markFailed(prompts);
    }
  }

  /**
   * Run `send`; if the backend dropped our session (409: restart, idle reaping), start a
   * new one for the same series and run it once more. The new session holds no object, so
   * `send` re-seeds it from the local mask before prompting.
   */
  async function withSessionRecovery<T>(source: SourceImage, send: () => Promise<T>): Promise<T> {
    try {
      return await send();
    } catch (error) {
      if (!serverApi.isSessionExpiredError(error)) {
        throw error;
      }
      sessionModel.markExpired();
      const ok = await sessionModel.initialize(servicesManager);
      if (!ok || !imageModel.sameSource(sessionModel.getSource(), source)) {
        throw error;
      }
      notify('nnInteractive session was restarted; continuing on the current object.', 'info');
      return send();
    }
  }

  /** Drop the backend's interaction history; in-flight responses become stale. */
  async function resetBackendObject() {
    const source = sessionModel.getSource();
    if (source) {
      try {
        await serverApi.resetInteractions(source);
      } catch (error) {
        handleServerError(error);
      }
    }
    objectModel.clearServerObject();
    sessionModel.bumpGeneration();
  }

  // ── Objects ──────────────────────────────────────────────────────────────────────────────

  function setActiveObject(object: ObjectRef) {
    const { segmentationId, segmentIndex } = object;
    const viewportId = viewportGridService.getActiveViewportId();
    try {
      if (viewportId) {
        segmentationService.setActiveSegmentation(viewportId, segmentationId);
      }
    } catch {
      // ignore — the segment set below still targets the right segmentation
    }
    try {
      segmentationService.setActiveSegment(segmentationId, segmentIndex);
    } catch {
      // ignore
    }
    // Objects share layers: the brush may only paint the active one.
    bridge.applyEditLocks(bridge.isManaged(segmentationId) ? object : null);
  }

  /** The object moved to another layer: re-key its bookkeeping and keep it selected. */
  function adoptMovedObject(from: ObjectRef, to: ObjectRef) {
    objectModel.renameObject(from, to);
    promptModel.renameObject(from, to);
    setActiveObject(to);
  }

  /** Record what a written crop left in the object (voxels or, for a full replace, none). */
  function noteWrittenCrop(applied: bridge.ApplyCropResult, scope: string) {
    if (applied.wroteVoxels) {
      objectModel.markNonEmpty(applied.object);
    } else if (scope === 'full') {
      objectModel.markEmpty(applied.object);
    }
  }

  /**
   * Make the backend hold the target object before prompts. Returns whether the prompt
   * submission still needs nninter_reset_first (a fresh/empty object with a stale buffer).
   */
  async function ensureBackendHoldsObject(
    source: SourceImage,
    object: ObjectRef
  ): Promise<boolean> {
    if (objectModel.isKnownEmpty(object)) {
      objectModel.clearServerObject();
      return true;
    }
    if (objectModel.holdsObject(object) && !objectModel.isDirty(object)) {
      return false;
    }
    const mask = bridge.readObjectMask(source, object);
    if (!mask) {
      // Empty object → nothing to seed; reset the backend buffer before prompts.
      objectModel.clearServerObject();
      return true;
    }
    await serverApi.setActiveObjectMask(source, mask);
    objectModel.setServerObject(object);
    objectModel.clearDirty(object);
    objectModel.setUndoable(false);
    return false;
  }

  // ── Prompts ──────────────────────────────────────────────────────────────────────────────

  // Serialize prompt submissions so rapid live-mode completions never double-send.
  let submitChain: Promise<void> = Promise.resolve();

  async function runNninter() {
    const source = await ensureSession();
    if (!source) {
      return;
    }

    // Convert annotation geometry → source voxel prompt arrays.
    const viewport = activeViewport();
    const arrays = emptyPromptArrays();
    const sent: any[] = [];
    for (const annotation of promptModel.getAllUnsubmitted()) {
      const kind = promptModel.kindOf(annotation);
      const conversion = kind && PROMPT_CONVERSION[kind];
      const prompt = conversion?.toVoxels(viewport, annotation, source.imageIds);
      if (prompt) {
        const sign = annotation.metadata.neg ? 'neg' : 'pos';
        arrays[`${sign}_${conversion.field}` as keyof PromptArrays].push(prompt);
        sent.push(annotation);
      }
    }
    if (!sent.length) {
      notify('No new prompts to run.', 'info');
      return;
    }

    // Refine the active object, or start a new one when none of ours is selected.
    const active = objectModel.getActiveObject(servicesManager);
    let target: ObjectRef;
    if (active && bridge.isManaged(active.segmentationId)) {
      target = active;
    } else {
      target = await bridge.addObject(servicesManager, commandsManager, source);
      objectModel.markEmpty(target);
    }
    setActiveObject(target);

    let crop: Awaited<ReturnType<typeof serverApi.submitPrompts>>;
    let generation: number;
    try {
      ({ crop, generation } = await withSessionRecovery(source, async () => {
        const generation = sessionModel.getGeneration();
        const resetFirst = await ensureBackendHoldsObject(source, target);
        return { generation, crop: await serverApi.submitPrompts(source, arrays, resetFirst) };
      }));
    } catch (error) {
      handleServerError(error, sent);
      return;
    }

    // Stale-response guard: a reset/re-init since the request started invalidates this crop.
    if (sessionModel.getGeneration() !== generation) {
      return;
    }

    objectModel.setServerObject(target);
    if (crop.meta.prompt_info !== 'no new prompts') {
      objectModel.setUndoable(true);
    }
    if (crop.scope !== 'unchanged' && crop.seg.length) {
      const applied = await bridge.applyCrop(
        servicesManager,
        commandsManager,
        source,
        target,
        crop
      );
      if (applied.moved) {
        adoptMovedObject(target, applied.object);
        target = applied.object;
      }
      noteWrittenCrop(applied, crop.scope);
    }
    objectModel.clearDirty(target);

    promptModel.markSubmitted(sent, target);
    if (!toolboxState.get().promptsVisible) {
      promptModel.setPromptsVisible(false, target);
    }
  }

  function nninter() {
    submitChain = submitChain.then(() =>
      runNninter().catch(e => {
        console.warn('[nninteractive] run failed:', e);
        notify(`nnInteractive could not apply the prompt: ${e?.message ?? e}`, 'error');
      })
    );
    return submitChain;
  }

  // ── Viewport guard + brush dirty tracking ────────────────────────────────────────────────

  // Coalesce bursts of viewport/representation events into one guard run at a time; an event
  // during a run queues exactly one more run.
  let guardQueued = false;
  let guardScheduled = false;
  let guardRunning = false;

  async function runViewportGuard() {
    guardScheduled = false;
    guardRunning = true;
    try {
      do {
        guardQueued = false;
        await bridge.ensureViewportRepresentations(servicesManager);
      } while (guardQueued);
    } catch (e) {
      console.error('[nninteractive] viewport guard failed:', e);
    } finally {
      guardRunning = false;
      if (guardQueued) {
        queueGuardRun();
      }
    }
  }

  function queueGuardRun() {
    if (!guardScheduled && !guardRunning) {
      guardScheduled = true;
      setTimeout(runViewportGuard, 0);
    }
  }

  const scheduleViewportGuard = () => {
    if (toolboxState.get().modeActive) {
      guardQueued = true;
      queueGuardRun();
    }
  };

  if (!subscriptionsInstalled) {
    subscriptionsInstalled = true;

    eventTarget.addEventListener(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, () => {
      if (!toolboxState.get().manualCorrectionMode) {
        return;
      }
      // Manual brush edit → mark the object dirty so the next prompt re-syncs its mask.
      const active = objectModel.getActiveObject(servicesManager);
      if (active) {
        objectModel.markDirty(active);
      }
    });

    const { EVENTS: VIEWPORT_EVENTS } = cornerstoneViewportService;
    cornerstoneViewportService.subscribe(
      VIEWPORT_EVENTS.VIEWPORT_VOLUMES_CHANGED,
      scheduleViewportGuard
    );
    cornerstoneViewportService.subscribe(
      VIEWPORT_EVENTS.VIEWPORT_DATA_CHANGED,
      scheduleViewportGuard
    );
    // OHIF propagates segmentations to new viewports (a Surface in 3D) after the viewport events
    // above, so re-run the guard whenever a representation is added.
    segmentationService.subscribe(
      segmentationService.EVENTS.SEGMENTATION_REPRESENTATION_MODIFIED,
      scheduleViewportGuard
    );

    // Import-split: a saved DICOM SEG is hydrated as ONE multi-segment segmentation; split it back
    // into managed objects. Deferred OUT of the hydration / viewport-mount call stack
    // (SEGMENTATION_ADDED fires synchronously inside createSegmentationForSEGDisplaySet; mutating
    // segmentation state mid-flow crashes the viewer), with bounded retries while hydration pixel
    // data settles.
    const SPLIT_RETRY_MS = 300;
    const SPLIT_MAX_RETRIES = 15;
    const trySplit = (segmentationId: string, retries = 0) => {
      bridge
        .importSplitSegmentation(
          servicesManager,
          commandsManager,
          segmentationId,
          sourceForSegmentation(segmentationId)
        )
        .then(result => {
          if (result.status !== 'retry') {
            return;
          }
          if (retries < SPLIT_MAX_RETRIES) {
            setTimeout(() => trySplit(segmentationId, retries + 1), SPLIT_RETRY_MS);
          } else {
            console.warn(
              `[nninteractive] import-split: giving up on ${segmentationId} (${result.reason}); original left as-is`
            );
          }
        })
        .catch(e => console.warn('[nninteractive] import-split error:', e));
    };
    segmentationService.subscribe(
      segmentationService.EVENTS.SEGMENTATION_ADDED,
      ({ segmentationId }) => {
        // Other modes keep OHIF's multi-segment SEG.
        if (toolboxState.get().modeActive && segmentationId) {
          setTimeout(() => trySplit(segmentationId), 250);
        }
      }
    );
  }

  // ── Export ───────────────────────────────────────────────────────────────────────────────

  // The objects to export: every object of the requested (or active) series. Empty when the
  // request targets a segmentation this extension does not manage (OHIF's own export runs).
  const resolveExportObjects = (args: any): ObjectRef[] => {
    const requestedId = args?.segmentationId;
    if (requestedId && !bridge.isManaged(requestedId)) {
      return [];
    }
    const seriesInstanceUID =
      (requestedId && bridge.getSeriesInstanceUIDForSegmentation(requestedId)) ||
      sessionModel.getSource()?.seriesInstanceUID;
    return seriesInstanceUID ? bridge.getObjectsForSeries(seriesInstanceUID) : bridge.getObjects();
  };

  const getExportColor = (
    { segmentationId, segmentIndex }: ObjectRef,
    segment: any,
    fallbackOrdinal: number
  ): number[] => {
    const representations =
      segmentationService.getRepresentationsForSegmentation(segmentationId) ?? [];
    const viewportId = representations[0]?.viewportId ?? viewportGridService.getActiveViewportId();
    if (viewportId) {
      try {
        const color = segmentationService.getSegmentColor(viewportId, segmentationId, segmentIndex);
        if (Array.isArray(color) && color.length >= 3) {
          return color;
        }
      } catch {
        // fall through to metadata color
      }
    }
    const color = segment?.cachedStats?.color ?? segment?.color;
    return Array.isArray(color) && color.length >= 3
      ? color
      : bridge.objectColorForOrdinal(fallbackOrdinal);
  };

  const buildMergedNninterSegmentation = (objects: ObjectRef[], options: any = {}) => {
    const firstSeg = segmentationService.getSegmentation(objects[0].segmentationId);
    const firstLabelmap = firstSeg?.representationData?.[LABELMAP];
    const firstImageIds = firstLabelmap?.imageIds ?? [];
    if (!firstImageIds.length) {
      throw new Error('No labelmap images found for nnInteractive export.');
    }

    const referencedImages = firstImageIds.map((imageId: string, index: number) => {
      const referencedImageId =
        (cache.getImage(imageId) as any)?.referencedImageId ??
        firstLabelmap?.referencedImageIds?.[index];
      return referencedImageId ? cache.getImage(referencedImageId) : null;
    });
    if (referencedImages.some((image: any) => !image)) {
      throw new Error('Referenced source images are not cached for nnInteractive export.');
    }

    const labelmaps: any[] = [];
    let exportSegmentNumber = 1;
    // Slices an object does not touch share one read-only zero buffer, so export memory
    // scales with the segmented slices rather than objects × volume.
    const emptySlices = new Map<string, ArrayLike<number>>();
    const emptySlice = (PixelArray: any, length: number) => {
      const key = `${PixelArray.name}:${length}`;
      if (!emptySlices.has(key)) {
        emptySlices.set(key, new PixelArray(length));
      }
      return emptySlices.get(key);
    };

    for (const object of objects) {
      const { segmentationId, segmentIndex } = object;
      const segmentation = segmentationService.getSegmentation(segmentationId);
      const imageIds = segmentation?.representationData?.[LABELMAP]?.imageIds ?? [];
      if (!segmentation || imageIds.length !== firstImageIds.length) {
        throw new Error(`Segmentation ${segmentationId} does not match the export source series.`);
      }

      const segment = segmentation.segments?.[segmentIndex];
      const labelmaps2D: any[] = [];
      let hasVoxels = false;

      for (let z = 0; z < imageIds.length; z++) {
        const segImage: any = cache.getImage(imageIds[z]);
        const referencedImage: any = referencedImages[z];
        const sourcePixels: ArrayLike<number> | undefined = segImage?.voxelManager?.getScalarData();
        if (!sourcePixels) {
          throw new Error(`Labelmap image ${z} is not cached for nnInteractive export.`);
        }
        const rows = segImage.rows ?? referencedImage?.rows;
        const columns = segImage.columns ?? referencedImage?.columns;
        if (!rows || !columns) {
          throw new Error(`Labelmap image ${z} is missing rows/columns for nnInteractive export.`);
        }

        // The layer holds several objects: only voxels with this object's index belong to it.
        const PixelArray = exportSegmentNumber > 255 ? Uint16Array : Uint8Array;
        let pixelData: any;
        for (let i = 0; i < sourcePixels.length; i++) {
          if (sourcePixels[i] === segmentIndex) {
            pixelData ??= new PixelArray(sourcePixels.length);
            pixelData[i] = exportSegmentNumber;
          }
        }
        hasVoxels ||= !!pixelData;

        labelmaps2D[z] = {
          segmentsOnLabelmap: pixelData ? [exportSegmentNumber] : [],
          pixelData: pixelData ?? emptySlice(PixelArray, sourcePixels.length),
          rows,
          columns,
        };
      }

      if (!hasVoxels) {
        continue;
      }

      const color = getExportColor(object, segment, exportSegmentNumber);
      const RecommendedDisplayCIELabValue = dcmjs.data.Colors.rgb2DICOMLAB(
        color.slice(0, 3).map((value: number) => value / 255)
      ).map((value: number) => Math.round(value));
      const metadata: any[] = [];
      metadata[exportSegmentNumber] = {
        SegmentNumber: exportSegmentNumber.toString(),
        SegmentLabel: segment?.label || `Object ${exportSegmentNumber}`,
        SegmentAlgorithmType: segment?.algorithmType || 'MANUAL',
        SegmentAlgorithmName: segment?.algorithmName || 'nnInteractive',
        RecommendedDisplayCIELabValue,
        SegmentedPropertyCategoryCodeSequence: TISSUE_CODE,
        SegmentedPropertyTypeCodeSequence: TISSUE_CODE,
      };

      labelmaps.push({ segmentsOnLabelmap: [exportSegmentNumber], metadata, labelmaps2D });
      exportSegmentNumber++;
    }

    if (!labelmaps.length) {
      throw new Error('No non-empty nnInteractive objects to export.');
    }

    const label =
      options.SeriesDescription ||
      firstSeg?.cachedStats?.seriesDescription ||
      `nnInteractive ${labelmaps.length} objects`;
    const generated = generateSegmentation(referencedImages, labelmaps, metaData, {
      ...options,
      SeriesDescription: label,
    });
    return { generated, label };
  };

  const resolveDataSource = (dataSourceName?: string) => {
    if (dataSourceName) {
      return extensionManager.getDataSources(dataSourceName)?.[0];
    }
    // getActiveDataSource() returns an ARRAY of data source instances in OHIF 3.x (a single
    // definition can back several), so unwrap it — otherwise `.store.dicom` is undefined.
    return extensionManager.getActiveDataSource()?.[0];
  };

  // ── Commands ─────────────────────────────────────────────────────────────────────────────

  const actions = {
    nninter,

    nninterSessionStatus: () => sessionModel.heartbeat(),

    closeNninterSession: () => sessionModel.close(),

    /** Called by the nnInteractive mode: the extension's global listeners act only in between. */
    enterNninterMode() {
      toolboxState.reset();
      toolboxState.set({ modeActive: true });
    },

    exitNninterMode() {
      sessionModel.close();
      objectModel.clearServerObject();
      promptModel.resetUndoOrder();
      toolboxState.reset();
    },

    async undoNninter() {
      const source = sessionModel.getSource();
      const active = objectModel.getActiveObject(servicesManager);
      if (!objectModel.isUndoable() || !source || !active) {
        return;
      }
      let result: Awaited<ReturnType<typeof serverApi.undo>>;
      try {
        result = await serverApi.undo(source);
      } catch (error) {
        handleServerError(error);
        return;
      }
      if (!result.undone) {
        return;
      }
      if (result.crop.seg.length) {
        let applied: bridge.ApplyCropResult;
        try {
          applied = await bridge.applyCrop(
            servicesManager,
            commandsManager,
            source,
            active,
            result.crop
          );
        } catch (error) {
          notify(
            `nnInteractive could not apply the undo: ${(error as Error)?.message ?? error}`,
            'error'
          );
          return;
        }
        if (applied.moved) {
          adoptMovedObject(active, applied.object);
        }
        noteWrittenCrop(applied, result.crop.scope);
      }
      promptModel.removeLastSubmitted();
    },

    async resetSegment(object: ObjectRef) {
      bridge.clearObject(object);
      promptModel.clearForObject(object);
      objectModel.markEmpty(object);
      if (objectModel.holdsObject(object)) {
        await resetBackendObject();
      }
    },

    // Not `deleteSegment`: OHIF's cornerstone extension owns that name and its context is searched first.
    async deleteNninterObject(object: ObjectRef) {
      const held = objectModel.holdsObject(object);
      // Drops the segment; deletes its layer once no object is left in it.
      await bridge.removeObject(commandsManager, object);
      promptModel.clearForObject(object);
      objectModel.forgetObject(object);
      if (held) {
        await resetBackendObject();
      }
    },

    /** Create and select the next empty object immediately. */
    async armNextNninterObject() {
      const source = await ensureSession();
      if (!source) {
        return;
      }
      let created: ObjectRef;
      try {
        created = await bridge.addObject(servicesManager, commandsManager, source);
      } catch (error) {
        console.error('[nninteractive] could not create an object:', error);
        notify(`Could not create a new object: ${(error as Error)?.message ?? error}`, 'error');
        return;
      }
      setActiveObject(created);
      promptModel.clearAll();
      objectModel.clearServerObject();
      objectModel.markEmpty(created);
      return created;
    },

    /** Select an existing object and make the backend hold its mask for refinement. */
    async loadSegmentForRefinement(object: ObjectRef) {
      setActiveObject(object);
      if (!bridge.isManaged(object.segmentationId)) {
        return;
      }
      const source = await ensureSession();
      if (!source) {
        return;
      }
      try {
        if (await ensureBackendHoldsObject(source, object)) {
          await serverApi.resetInteractions(source);
          sessionModel.bumpGeneration();
        }
      } catch (error) {
        console.error('[nninteractive] load segment for refinement failed:', error);
        handleServerError(error);
      }
    },

    jumpToSegment() {
      const active = objectModel.getActiveObject(servicesManager);
      const viewportId = viewportGridService.getActiveViewportId();
      const center =
        active && viewportId && !objectModel.isKnownEmpty(active) && bridge.objectCenter(active);
      if (!center) {
        return; // no voxels to center on
      }
      try {
        // Positional args up to the last one, the precomputed center; undefined keeps OHIF's defaults.
        segmentationService.jumpToSegmentCenter(
          active.segmentationId,
          active.segmentIndex,
          viewportId,
          undefined,
          undefined,
          undefined,
          undefined,
          undefined,
          center
        );
      } catch {
        // viewport cannot jump (e.g. 3D)
      }
    },

    /** Export nnInteractive objects to one overlapping DICOM SEG. */
    async storeNninterSegmentation(args: any) {
      const objects = resolveExportObjects(args);
      if (!objects.length) {
        return commandsManager.run('storeSegmentation', args);
      }

      // Prompt for a series name (and, if configured, a target data source) before storing —
      // same dialog OHIF uses for its own SEG export.
      const {
        value: reportName,
        dataSourceName,
        action,
      } = await createReportDialogPrompt({
        servicesManager,
        extensionManager,
        title: 'Store nnInteractive Segmentation',
      });
      if (action !== PROMPT_RESPONSES.CREATE_REPORT) {
        return;
      }

      const options = {
        ...args?.options,
        ...(reportName ? { SeriesDescription: reportName } : {}),
      };
      const { generated } = buildMergedNninterSegmentation(objects, options);
      const dataSource = resolveDataSource(dataSourceName);
      if (!dataSource?.store?.dicom) {
        throw new Error('No DICOM store data source is available for nnInteractive export.');
      }
      const naturalizedReport = generated.dataset;
      await dataSource.store.dicom(naturalizedReport);
      const wadoRoot = dataSource.getConfig?.().wadoRoot;
      if (wadoRoot) {
        naturalizedReport.wadoRoot = wadoRoot;
      }
      DicomMetadataStore.addInstances([naturalizedReport], true);
      notify('Stored merged nnInteractive DICOM SEG.', 'success');
      return naturalizedReport;
    },

    async downloadNninterSegmentation(args: any) {
      const objects = resolveExportObjects(args);
      if (!objects.length) {
        return commandsManager.run('downloadSegmentation', args);
      }
      const { generated, label } = buildMergedNninterSegmentation(objects, args?.options);
      downloadDICOMData(generated.dataset, label);
      return generated.dataset;
    },
  };

  const definitions: Record<string, { commandFn: (...args: any[]) => any; context?: string }> =
    Object.fromEntries(Object.entries(actions).map(([name, commandFn]) => [name, { commandFn }]));
  definitions.storeNninterSegmentation.context = 'SEGMENTATION';
  definitions.downloadNninterSegmentation.context = 'SEGMENTATION';

  return { actions, definitions, defaultContext: 'DEFAULT' };
};

export default commandsModule;
