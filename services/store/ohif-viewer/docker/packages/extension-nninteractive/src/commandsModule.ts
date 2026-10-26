// Thin command layer. Every command delegates to a small model module — the command
// module owns no data model, no server bookkeeping, and no viewport internals.
//
// See docs/nninteractive-ohif-ideal-architecture.md §6 (Commands) and §16 (module map).

import dcmjs from 'dcmjs';
import {
  BaseVolumeViewport,
  VolumeViewport3D,
  cache,
  eventTarget,
  metaData,
} from '@cornerstonejs/core';
import { Enums as csToolsEnums } from '@cornerstonejs/tools';
import { adaptersSEG, helpers } from '@cornerstonejs/adapters';
import { DicomMetadataStore } from '@ohif/core';
import { createReportDialogPrompt } from '@ohif/extension-default';
// PROMPT_RESPONSES is not re-exported from the package index; reach into OHIF's default
// extension source (this extension lives alongside it under packages/, so the relative
// path resolves at build time — same import the pre-rewrite commandsModule used).
import PROMPT_RESPONSES from '../../default/src/utils/_shared/PROMPT_RESPONSES';

import * as sessionModel from './model/sessionModel';
import * as serverApi from './model/serverApi';
import * as objectModel from './model/objectModel';
import * as promptModel from './model/promptModel';
import * as imageModel from './model/imageModel';
import * as coord from './model/coordinateMapping';
import * as bridge from './model/segmentationBridge';
import { debugSnapshot, installDebugHook } from './model/debugTools';
import { emptyPromptArrays, objectKeyOf, type SourceImage } from './model/types';
import { toolboxState } from './utils/toolboxState';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;
const {
  Cornerstone3D: {
    Segmentation: { generateSegmentation },
  },
} = adaptersSEG;
const { downloadDICOMData } = helpers;

// Guard so the MPR/brush event subscriptions are installed only once, even if
// getCommandsModule is ever invoked more than once.
let subscriptionsInstalled = false;

const commandsModule = ({ servicesManager, commandsManager, extensionManager }: any) => {
  const services = servicesManager.services;
  const {
    viewportGridService,
    cornerstoneViewportService,
    segmentationService,
    uiNotificationService,
    displaySetService,
  } = services;

  // Resolve the source image series for a segmentation from its OWN referenced images (so a SEG
  // imported into a multi-series study splits onto the right series regardless of which viewport
  // is active), falling back to the active viewport's source.
  const sourceForSegmentation = (segmentationId: string): SourceImage | null => {
    const seg = segmentationService.getSegmentation(segmentationId);
    const refIds = seg?.representationData?.[LABELMAP]?.referencedImageIds ?? [];
    const firstRef = refIds[0];
    const instance = firstRef ? metaData.get('instance', firstRef) : null;
    const SOPInstanceUID = instance?.SOPInstanceUID || instance?.SopInstanceUID;
    const SeriesInstanceUID = instance?.SeriesInstanceUID;
    const displaySet =
      SOPInstanceUID && displaySetService?.getDisplaySetForSOPInstanceUID
        ? displaySetService.getDisplaySetForSOPInstanceUID(SOPInstanceUID, SeriesInstanceUID)
        : null;
    if (displaySet?.SeriesInstanceUID && Array.isArray(displaySet.imageIds) && displaySet.imageIds.length) {
      return {
        studyInstanceUID: displaySet.StudyInstanceUID,
        seriesInstanceUID: displaySet.SeriesInstanceUID,
        displaySetInstanceUID: displaySet.displaySetInstanceUID,
        imageIds: displaySet.imageIds,
        seriesDescription: displaySet.SeriesDescription,
      };
    }
    return imageModel.getActiveSource(servicesManager);
  };

  const notify = (message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') =>
    uiNotificationService?.show?.({ title: 'nnInteractive', message, type });

  const activeViewport = () => {
    const id = viewportGridService.getActiveViewportId?.();
    return id ? cornerstoneViewportService.getCornerstoneViewport(id) : undefined;
  };

  installDebugHook(servicesManager);

  const resolveManagedExportSegmentationIds = (args: any): string[] => {
    const requestedId = args?.segmentationId;
    if (requestedId && !bridge.isManaged(requestedId)) {
      return [];
    }

    const source = sessionModel.getSource();
    const seriesInstanceUID =
      (requestedId && bridge.getSeriesInstanceUIDForSegmentation(requestedId)) ||
      source?.seriesInstanceUID;
    const ids = seriesInstanceUID
      ? bridge.getManagedSegmentationIdsForSeries(seriesInstanceUID)
      : bridge.getManagedSegmentationIds();

    return ids.length ? ids : requestedId ? [requestedId] : [];
  };

  const getImagePixelData = (image: any): ArrayLike<number> | null =>
    image?.getPixelData?.() ?? image?.voxelManager?.getScalarData?.() ?? null;

  const getExportColor = (segmentationId: string, segment: any, fallbackOrdinal: number): number[] => {
    const representations = segmentationService.getRepresentationsForSegmentation?.(segmentationId) ?? [];
    const viewportId = representations[0]?.viewportId ?? viewportGridService.getActiveViewportId?.();
    if (viewportId && typeof segmentationService.getSegmentColor === 'function') {
      try {
        const color = segmentationService.getSegmentColor(viewportId, segmentationId, 1);
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

  const buildMergedNninterSegmentation = (segmentationIds: string[], options: any = {}) => {
    const firstSeg = segmentationService.getSegmentation(segmentationIds[0]);
    const firstLabelmap = firstSeg?.representationData?.[LABELMAP];
    const firstImageIds = firstLabelmap?.imageIds ?? [];
    if (!firstImageIds.length) {
      throw new Error('No labelmap images found for nnInteractive export.');
    }

    const firstSegImages = firstImageIds.map((imageId: string) => cache.getImage(imageId));
    const referencedImages = firstSegImages.map((segImage: any, index: number) => {
      const referencedImageId =
        segImage?.referencedImageId ?? firstLabelmap?.referencedImageIds?.[index];
      return referencedImageId ? cache.getImage(referencedImageId) : null;
    });
    if (referencedImages.some((image: any) => !image)) {
      throw new Error('Referenced source images are not cached for nnInteractive export.');
    }

    const labelmaps: any[] = [];
    let exportSegmentNumber = 1;

    for (const segmentationId of segmentationIds) {
      const segmentation = segmentationService.getSegmentation(segmentationId);
      const labelmap = segmentation?.representationData?.[LABELMAP];
      const imageIds = labelmap?.imageIds ?? [];
      if (!segmentation || imageIds.length !== firstImageIds.length) {
        throw new Error(`Segmentation ${segmentationId} does not match the export source series.`);
      }

      const segment = segmentation.segments?.[1] ?? segmentation.segments?.['1'];
      const labelmaps2D: any[] = [];
      let hasVoxels = false;

      for (let z = 0; z < imageIds.length; z++) {
        const segImage: any = cache.getImage(imageIds[z]);
        const referencedImage: any = referencedImages[z];
        const sourcePixels = getImagePixelData(segImage);
        if (!segImage || !sourcePixels) {
          throw new Error(`Labelmap image ${z} is not cached for nnInteractive export.`);
        }
        const rows = segImage.rows ?? referencedImage?.rows;
        const columns = segImage.columns ?? referencedImage?.columns;
        if (!rows || !columns) {
          throw new Error(`Labelmap image ${z} is missing rows/columns for nnInteractive export.`);
        }

        const PixelArray = exportSegmentNumber > 255 ? Uint16Array : Uint8Array;
        const pixelData = new PixelArray(sourcePixels.length);
        let hasSliceVoxels = false;
        for (let i = 0; i < sourcePixels.length; i++) {
          if (sourcePixels[i] !== 0) {
            pixelData[i] = exportSegmentNumber;
            hasSliceVoxels = true;
          }
        }
        if (hasSliceVoxels) {
          hasVoxels = true;
        }

        labelmaps2D[z] = {
          segmentsOnLabelmap: hasSliceVoxels ? [exportSegmentNumber] : [],
          pixelData,
          rows,
          columns,
        };
      }

      if (!hasVoxels) {
        continue;
      }

      const color = getExportColor(segmentationId, segment, exportSegmentNumber);
      const RecommendedDisplayCIELabValue = dcmjs.data.Colors.rgb2DICOMLAB(
        color.slice(0, 3).map((value: number) => value / 255)
      ).map((value: number) => Math.round(value));
      const metadata: any[] = [];
      metadata[exportSegmentNumber] = {
        SegmentNumber: exportSegmentNumber.toString(),
        SegmentLabel: segment?.label || segmentation.label || `Object ${exportSegmentNumber}`,
        SegmentAlgorithmType: segment?.algorithmType || 'MANUAL',
        SegmentAlgorithmName: segment?.algorithmName || 'nnInteractive',
        RecommendedDisplayCIELabValue,
        SegmentedPropertyCategoryCodeSequence: {
          CodeValue: 'T-D0050',
          CodingSchemeDesignator: 'SRT',
          CodeMeaning: 'Tissue',
        },
        SegmentedPropertyTypeCodeSequence: {
          CodeValue: 'T-D0050',
          CodingSchemeDesignator: 'SRT',
          CodeMeaning: 'Tissue',
        },
      };

      labelmaps.push({
        segmentsOnLabelmap: [exportSegmentNumber],
        metadata,
        labelmaps2D,
      });
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

  const resolveDataSource = (dataSource: any) => {
    if (dataSource && typeof dataSource === 'string') {
      return extensionManager?.getDataSources?.(dataSource)?.[0];
    }
    // extensionManager.getActiveDataSource() returns an ARRAY of data source
    // instances in OHIF 3.x (a single definition can back several), so unwrap it —
    // otherwise `.store.dicom` is undefined and export bails.
    const resolved = dataSource ?? extensionManager?.getActiveDataSource?.();
    return Array.isArray(resolved) ? resolved[0] : resolved;
  };

  async function setActiveObject(segmentationId: string, segmentIndex: number) {
    const resolvedSegmentIndex = bridge.isManaged(segmentationId) ? 1 : segmentIndex;
    try {
      const viewportId = viewportGridService.getActiveViewportId?.();
      if (viewportId) {
        segmentationService.setActiveSegmentation?.(viewportId, segmentationId);
      }
    } catch {
      // ignore — the segment set below still targets the right segmentation
    }
    try {
      segmentationService.setActiveSegment?.(segmentationId, resolvedSegmentIndex);
    } catch {
      // ignore
    }
    toolboxState.setCurrentActiveSegment(resolvedSegmentIndex);
  }

  function handleServerError(error: any, prompts?: any[]) {
    if (serverApi.isSessionExpiredError(error)) {
      sessionModel.markExpired();
      toolboxState.setSessionActive(false);
      notify('nnInteractive session expired. Please re-initialize.', 'warning');
    } else {
      notify(`nnInteractive request failed: ${error?.message ?? error}`, 'error');
    }
    if (prompts?.length) {
      promptModel.markFailed(prompts);
    }
  }

  /**
   * Make the backend hold the target object before prompts. Returns whether the prompt
   * submission still needs nninter_reset_first (a fresh/empty object with a stale buffer).
   */
  async function ensureBackendHoldsObject(
    source: any,
    segmentationId: string,
    segmentIndex: number,
    isNew: boolean
  ): Promise<boolean> {
    if (isNew || objectModel.isKnownEmpty(segmentationId, segmentIndex)) {
      objectModel.clearServerObject();
      return true;
    }
    const holds = objectModel.holdsObject(segmentationId, segmentIndex);
    const objectDirty = objectModel.isDirty(segmentationId, segmentIndex);
    const mprDirty = bridge.isMprDirty(segmentationId);
    const dirty = objectDirty || mprDirty;
    if (holds && !dirty) {
      return false;
    }
    if (mprDirty) {
      bridge.flushAuthoritativeLabelmap(servicesManager, segmentationId, 'volumeToStack');
    } else if (objectDirty) {
      bridge.flushAuthoritativeLabelmap(servicesManager, segmentationId, 'stackToVolume');
    }
    const mask = bridge.readObjectMask(servicesManager, source, segmentationId, segmentIndex);
    if (mask) {
      await serverApi.setActiveObjectMask(source, mask);
      objectModel.setServerObject(segmentationId, segmentIndex);
      objectModel.clearDirty(segmentationId, segmentIndex);
      objectModel.setUndoable(false);
      return false;
    }
    // Empty object → nothing to seed; reset the backend buffer before prompts.
    objectModel.clearServerObject();
    return true;
  }

  // Serialize prompt submissions so rapid live-mode completions never double-send.
  let submitChain: Promise<any> = Promise.resolve();

  async function runNninter() {
    if (toolboxState.getLocked()) {
      return;
    }
    if (!sessionModel.isReadyForActive(servicesManager)) {
      const ok = await sessionModel.initialize(servicesManager);
      toolboxState.setSessionActive(ok);
      if (!ok) {
        notify('Could not start an nnInteractive session for this series.', 'warning');
        return;
      }
    }
    const source = sessionModel.getSource();
    if (!source) {
      return;
    }
    const generation = sessionModel.getGeneration();
    const viewport = activeViewport();

    const pending = promptModel.getAllUnsubmitted();
    if (!pending.length) {
      notify('No new prompts to run.', 'info');
      return;
    }

    // Resolve the target object: new object if armed or no active managed object; else refine.
    const active = objectModel.getActiveObject(servicesManager);
    const activeIsManaged = !!active && bridge.isManaged(active.segmentationId);
    let target: { segmentationId: string; segmentIndex: number };
    let isNew = false;
    if (toolboxState.getRefineNew() || !activeIsManaged) {
      const created = await bridge.addObject(servicesManager, commandsManager, source);
      target = { segmentationId: created.segmentationId, segmentIndex: created.segmentIndex };
      isNew = true;
      objectModel.markEmpty(target.segmentationId, target.segmentIndex);
      toolboxState.setRefineNew(false);
    } else {
      target = {
        segmentationId: active.segmentationId,
        segmentIndex: bridge.isManaged(active.segmentationId) ? 1 : active.segmentIndex,
      };
    }
    await setActiveObject(target.segmentationId, target.segmentIndex);
    const targetKey = objectKeyOf(target.segmentationId, target.segmentIndex);

    let resetFirst: boolean;
    try {
      resetFirst = await ensureBackendHoldsObject(source, target.segmentationId, target.segmentIndex, isNew);
    } catch (error) {
      handleServerError(error);
      return;
    }

    // Convert annotation geometry → source voxel prompt arrays.
    const arrays = emptyPromptArrays();
    const sent: any[] = [];
    for (const annotation of pending) {
      const neg = !!annotation.metadata?.neg;
      const kind = promptModel.kindOf(annotation);
      if (kind === 'point') {
        const p = coord.pointIJK(viewport, annotation, source.imageIds);
        if (!p) {
          continue;
        }
        (neg ? arrays.neg_points : arrays.pos_points).push(p);
      } else if (kind === 'box') {
        const b = coord.boxIJK(viewport, annotation, source.imageIds);
        if (!b) {
          continue;
        }
        (neg ? arrays.neg_boxes : arrays.pos_boxes).push(b);
      } else if (kind === 'lasso') {
        const l = coord.freehandPromptIJK(viewport, annotation, source.imageIds);
        if (!l) {
          continue;
        }
        (neg ? arrays.neg_lassos : arrays.pos_lassos).push(l);
      } else if (kind === 'scribble') {
        const s = coord.freehandPromptIJK(viewport, annotation, source.imageIds);
        if (!s) {
          continue;
        }
        (neg ? arrays.neg_scribbles : arrays.pos_scribbles).push(s);
      } else {
        continue;
      }
      sent.push(annotation);
    }
    if (!sent.length) {
      notify('No new prompts to run.', 'info');
      return;
    }

    let crop;
    try {
      crop = await serverApi.submitPrompts(source, arrays, resetFirst);
    } catch (error) {
      handleServerError(error, sent);
      return;
    }

    // Stale-response guard: a reset/re-init since the request started invalidates this crop.
    if (sessionModel.getGeneration() !== generation) {
      return;
    }

    objectModel.setServerObject(target.segmentationId, target.segmentIndex);
    const accepted = String(crop.meta?.prompt_info ?? '').toLowerCase() !== 'no new prompts';
    if (accepted) {
      objectModel.setUndoable(true);
    }
    if (crop.scope !== 'unchanged' && crop.seg.length) {
      const applied = await bridge.applyCrop(
        servicesManager,
        target.segmentationId,
        target.segmentIndex,
        crop
      );
      if (applied.wroteVoxels) {
        objectModel.markNonEmpty(target.segmentationId, target.segmentIndex);
      } else if (crop.scope === 'full') {
        objectModel.markEmpty(target.segmentationId, target.segmentIndex);
      }
    }
    objectModel.clearDirty(target.segmentationId, target.segmentIndex);

    for (const annotation of sent) {
      if (annotation.metadata) {
        annotation.metadata.objectKey = targetKey;
      }
    }
    promptModel.markSubmitted(sent);
    if (!toolboxState.getPromptsVisible()) {
      promptModel.setPromptsVisible(false, targetKey);
    }
  }

  function nninter() {
    submitChain = submitChain.then(() => runNninter().catch(e => console.warn('[nninteractive] run failed:', e)));
    return submitChain;
  }

  // ── MPR guard + brush dirty tracking ──────────────────────────────────────────────
  let guardQueued = false;
  let guardScheduled = false;
  let guardRunning = false;
  async function runMprGuard() {
    guardScheduled = false;
    if (guardRunning) {
      return;
    }
    guardRunning = true;
    try {
      do {
        guardQueued = false;
        await bridge.ensureMprForManagedSegmentations(servicesManager);
      } while (guardQueued);
    } catch (e) {
      console.error('[nninteractive] MPR guard failed:', e);
      throw e;
    } finally {
      guardRunning = false;
      if (guardQueued) {
        queueMprGuardRun();
      }
    }
  }
  const queueMprGuardRun = () => {
    if (guardScheduled || guardRunning) {
      return;
    }
    guardScheduled = true;
    setTimeout(() => {
      void runMprGuard();
    }, 0);
  };

  const scheduleMprGuard = () => {
    guardQueued = true;
    queueMprGuardRun();
  };

  if (!subscriptionsInstalled) {
    subscriptionsInstalled = true;

    eventTarget.addEventListener(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, () => {
      if (!toolboxState.getManualCorrectionMode()) {
        return;
      }
      const active = objectModel.getActiveObject(servicesManager);
      if (!active) {
        return;
      }
      // Manual brush edit → mark the object dirty so the next prompt re-syncs its mask.
      objectModel.markDirty(active.segmentationId, active.segmentIndex);
      const vp = activeViewport();
      if (vp instanceof BaseVolumeViewport && !(vp instanceof VolumeViewport3D)) {
        bridge.markMprDirty(active.segmentationId);
      }
    });

    const subscribeGuard = (service: any, eventKeys: string[]) => {
      if (!service?.subscribe || !service.EVENTS) {
        return;
      }
      for (const key of eventKeys) {
        const event = service.EVENTS[key];
        if (event) {
          try {
            service.subscribe(event, scheduleMprGuard);
          } catch {
            // ignore
          }
        }
      }
    };
    subscribeGuard(cornerstoneViewportService, ['VIEWPORT_VOLUMES_CHANGED', 'VIEWPORT_DATA_CHANGED']);

    // Import-split: a saved DICOM SEG is hydrated as ONE multi-segment segmentation; split it back
    // into N managed one-segment objects (the per-object model). Deferred OUT of the hydration /
    // viewport-mount call stack (SEGMENTATION_ADDED fires synchronously inside
    // createSegmentationForSEGDisplaySet; mutating segmentation state mid-flow crashes the viewer),
    // with bounded retries while hydration pixel data settles.
    const splitRetries = new Map<string, number>();
    const trySplit = (segmentationId: string) => {
      bridge
        .importSplitSegmentation(
          servicesManager,
          commandsManager,
          segmentationId,
          sourceForSegmentation(segmentationId)
        )
        .then(result => {
          if (result.status === 'retry') {
            const n = (splitRetries.get(segmentationId) ?? 0) + 1;
            splitRetries.set(segmentationId, n);
            if (n <= 15) {
              setTimeout(() => trySplit(segmentationId), 300);
            } else {
              console.warn(
                `[nninteractive] import-split: giving up on ${segmentationId} (${result.reason}); original left as-is`
              );
              splitRetries.delete(segmentationId);
            }
          } else {
            splitRetries.delete(segmentationId);
          }
        })
        .catch(e => console.warn('[nninteractive] import-split error:', e));
    };
    const segEvents: any = (segmentationService as any).EVENTS || {};
    if (segEvents.SEGMENTATION_ADDED && typeof segmentationService.subscribe === 'function') {
      segmentationService.subscribe(segEvents.SEGMENTATION_ADDED, (payload: any) => {
        const id = payload?.segmentationId ?? payload?.segmentation?.segmentationId;
        if (id) {
          setTimeout(() => trySplit(id), 250);
        }
      });
    }
  }

  const actions = {
    /** Activate a prompt/brush tool; forces Pan while the toolbox is locked. */
    setAiToolActive: ({ toolName }: { toolName: string }) => {
      const name = toolboxState.getLocked() ? 'Pan' : toolName;
      return commandsManager.run('setToolActive', { toolName: name });
    },

    /**
     * Toolbar toggle for prompt tools. The toolbar passes the tool name as `itemId`
     * (and sometimes `value`), NOT `toolName` — resolve all three. Arming a prompt tool
     * exits manual-correction mode; toggling the active tool off falls back to Pan.
     */
    toggleToolActiveToolbar: ({ value, itemId, toolName, toolGroupIds = [] }: any) => {
      const toolGroupService = services.toolGroupService;
      const resolvedToolName = toolName || itemId || value;
      const groups = toolGroupIds.length ? toolGroupIds : toolGroupService.getToolGroupIds();

      const { activeViewportId } = viewportGridService.getState();
      const activeToolGroup = toolGroupService.getToolGroupForViewport(activeViewportId);
      const isCurrentlyActive =
        activeToolGroup?.getActivePrimaryMouseButtonTool?.() === resolvedToolName;

      if (isCurrentlyActive) {
        groups.forEach((toolGroupId: string) => {
          const tg = toolGroupService.getToolGroup(toolGroupId);
          if (tg?.hasTool(resolvedToolName)) {
            tg.setToolPassive(resolvedToolName);
          }
          if (tg?.hasTool('Pan')) {
            commandsManager.run('setToolActive', { toolName: 'Pan', toolGroupId });
          }
        });
        toolboxState.setTool('none');
        return;
      }

      toolboxState.setTool(resolvedToolName);
      toolboxState.setManualCorrectionMode(false);
      commandsManager.run('setToolActiveToolbar', {
        value,
        itemId,
        toolName: resolvedToolName,
        toolGroupIds: groups,
      });
    },

    runAiSegmentation: () => {
      if (toolboxState.getLocked()) {
        return;
      }
      return nninter();
    },

    nninter: () => nninter(),

    async initNninter() {
      const ok = await sessionModel.initialize(servicesManager);
      toolboxState.setSessionActive(ok);
      const source = sessionModel.getSource();
      if (source) {
        toolboxState.setSessionSeries(source.seriesInstanceUID);
      }
      notify(
        ok ? 'nnInteractive session ready.' : 'Could not start an nnInteractive session.',
        ok ? 'success' : 'error'
      );
      return ok;
    },

    async nninterSessionStatus() {
      const active = await sessionModel.heartbeat();
      toolboxState.setSessionActive(active);
      return active;
    },

    closeNninterSession() {
      sessionModel.close();
      toolboxState.setSessionActive(false);
    },

    async undoNninter() {
      if (!objectModel.isUndoable()) {
        return;
      }
      const source = sessionModel.getSource();
      const active = objectModel.getActiveObject(servicesManager);
      if (!source || !active) {
        return;
      }
      let result;
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
        const applied = await bridge.applyCrop(
          servicesManager,
          active.segmentationId,
          active.segmentIndex,
          result.crop
        );
        if (applied.wroteVoxels) {
          objectModel.markNonEmpty(active.segmentationId, active.segmentIndex);
        } else if (result.crop.scope === 'full') {
          objectModel.markEmpty(active.segmentationId, active.segmentIndex);
        }
      }
      promptModel.removeLastSubmitted();
    },

    async resetNninter() {
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
    },

    async resetSegment({ segmentationId, segmentIndex }: any) {
      const resolvedSegmentIndex = bridge.isManaged(segmentationId) ? 1 : segmentIndex;
      await bridge.clearSegment(servicesManager, segmentationId, resolvedSegmentIndex);
      promptModel.clearForObject(objectKeyOf(segmentationId, resolvedSegmentIndex));
      objectModel.markEmpty(segmentationId, resolvedSegmentIndex);
      if (objectModel.holdsObject(segmentationId, resolvedSegmentIndex)) {
        await actions.resetNninter();
      }
    },

    async deleteSegment({ segmentationId, segmentIndex }: any) {
      const resolvedSegmentIndex = bridge.isManaged(segmentationId) ? 1 : segmentIndex;
      const held = objectModel.holdsObject(segmentationId, resolvedSegmentIndex);
      const managed = bridge.isManaged(segmentationId);
      await bridge.removeSegment(servicesManager, segmentationId, resolvedSegmentIndex);
      promptModel.clearForObject(objectKeyOf(segmentationId, resolvedSegmentIndex));
      objectModel.forgetObject(segmentationId, resolvedSegmentIndex);
      if (managed) {
        try {
          await commandsManager.run('deleteSegmentation', { segmentationId });
        } finally {
          bridge.unregisterManagedSegmentation(segmentationId);
        }
      }
      if (held) {
        await actions.resetNninter();
      }
    },

    /** Create and select the next empty object immediately. */
    async armNextNninterObject() {
      if (!sessionModel.isReadyForActive(servicesManager)) {
        const ok = await sessionModel.initialize(servicesManager);
        toolboxState.setSessionActive(ok);
        if (!ok) {
          notify('Could not start an nnInteractive session for this series.', 'warning');
          return;
        }
      }

      const source = sessionModel.getSource();
      if (!source) {
        notify('No source image series is active.', 'warning');
        return;
      }
      toolboxState.setSessionSeries(source.seriesInstanceUID);

      const created = await bridge.addObject(servicesManager, commandsManager, source);
      await setActiveObject(created.segmentationId, created.segmentIndex);
      toolboxState.setRefineNew(false);
      promptModel.clearAll();
      objectModel.clearServerObject();
      objectModel.markEmpty(created.segmentationId, created.segmentIndex);
      return created;
    },

    /** Select an existing object and make the backend hold its mask for refinement. */
    async loadSegmentForRefinement({ segmentationId, segmentIndex }: any) {
      const resolvedSegmentIndex = bridge.isManaged(segmentationId) ? 1 : segmentIndex;
      await setActiveObject(segmentationId, resolvedSegmentIndex);
      toolboxState.setRefineNew(false);
      if (!bridge.isManaged(segmentationId)) {
        return { loaded: false, reason: 'unmanaged-segmentation' };
      }
      if (!sessionModel.isReadyForActive(servicesManager)) {
        const ok = await sessionModel.initialize(servicesManager);
        toolboxState.setSessionActive(ok);
        if (!ok) {
          notify('Could not start an nnInteractive session for this series.', 'warning');
          return { loaded: false, reason: 'session-not-ready' };
        }
      }

      const source = sessionModel.getSource();
      if (!source) {
        notify('No source image series is active.', 'warning');
        return { loaded: false, reason: 'no-source' };
      }
      toolboxState.setSessionSeries(source.seriesInstanceUID);

      try {
        const resetFirst = await ensureBackendHoldsObject(
          source,
          segmentationId,
          resolvedSegmentIndex,
          false
        );
        if (resetFirst) {
          await serverApi.resetInteractions(source);
          sessionModel.bumpGeneration();
          objectModel.clearServerObject();
          objectModel.setUndoable(false);
        }
        return { loaded: true };
      } catch (error) {
        console.error('[nninteractive] load segment for refinement failed:', error);
        handleServerError(error);
        return { loaded: false, reason: 'backend-sync-failed' };
      }
    },

    jumpToSegment() {
      const active = objectModel.getActiveObject(servicesManager);
      const vpId = viewportGridService.getActiveViewportId?.();
      if (active && vpId) {
        segmentationService.jumpToSegmentCenter?.(active.segmentationId, active.segmentIndex, vpId);
      }
    },

    toggleCurrentSegment() {
      const vpId = viewportGridService.getActiveViewportId?.();
      const activeSeg = vpId ? segmentationService.getActiveSegmentation?.(vpId) : undefined;
      if (activeSeg) {
        segmentationService.toggleSegmentationRepresentationVisibility(vpId, {
          segmentationId: activeSeg.segmentationId,
          type: LABELMAP,
        });
      }
    },

    // Segment-level measurement toggles are not part of the nnInteractive prompt model
    // (prompts are annotations). Provided as safe no-ops so the segmentation table, which
    // renders these controls generically, never invokes a missing command.
    getSegmentMeasurementVisibility: () => false,
    toggleSegmentMeasurement: () => {},

    toggleSegmentationVisibilityAllViewports({ segmentationId, type }: any) {
      for (const vpId of cornerstoneViewportService.getViewportIds?.() ?? []) {
        try {
          segmentationService.toggleSegmentationRepresentationVisibility(vpId, {
            segmentationId,
            type: type ?? LABELMAP,
          });
        } catch {
          // ignore
        }
      }
    },

    async removeSegmentationFromViewport({ segmentationId }: any) {
      await actions.resetNninter();
      const vpId = viewportGridService.getActiveViewportId?.();
      if (vpId) {
        segmentationService.removeSegmentationRepresentations(vpId, { segmentationId });
      }
    },

    /** Export nnInteractive objects to one overlapping DICOM SEG. */
    async storeNninterSegmentation(args: any) {
      const managedIds = resolveManagedExportSegmentationIds(args);
      if (!managedIds.length) {
        return commandsManager.run('storeSegmentation', args);
      }

      // Prompt for a series name (and, if configured, a target data source) before storing —
      // same dialog OHIF uses for its own SEG export.
      const {
        value: reportName,
        dataSourceName: selectedDataSourceName,
        action,
      } = await createReportDialogPrompt({
        servicesManager,
        extensionManager,
        title: 'Store nnInteractive Segmentation',
      });
      if (action !== PROMPT_RESPONSES.CREATE_REPORT) {
        return;
      }

      for (const segId of managedIds) {
        bridge.flushAuthoritativeLabelmap(servicesManager, segId, 'volumeToStack');
      }
      const options = {
        ...args?.options,
        ...(reportName ? { SeriesDescription: reportName } : {}),
      };
      const { generated } = buildMergedNninterSegmentation(managedIds, options);
      const dataSource = resolveDataSource(selectedDataSourceName ?? args?.dataSource);
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
      const managedIds = resolveManagedExportSegmentationIds(args);
      if (!managedIds.length) {
        return commandsManager.run('downloadSegmentation', args);
      }
      for (const segId of managedIds) {
        bridge.flushAuthoritativeLabelmap(servicesManager, segId, 'volumeToStack');
      }
      const { generated, label } = buildMergedNninterSegmentation(managedIds, args?.options);
      downloadDICOMData(generated.dataset, label);
      return generated.dataset;
    },

    debugSnapshot: () => debugSnapshot(servicesManager),
  };

  const defaultContextNames = [
    'setAiToolActive',
    'runAiSegmentation',
    'initNninter',
    'nninterSessionStatus',
    'closeNninterSession',
    'undoNninter',
    'resetNninter',
    'resetSegment',
    'deleteSegment',
    'loadSegmentForRefinement',
    'armNextNninterObject',
    'nninter',
    'jumpToSegment',
    'toggleCurrentSegment',
    'debugSnapshot',
  ];

  const definitions: Record<string, any> = {};
  for (const name of defaultContextNames) {
    definitions[name] = { commandFn: (actions as any)[name] };
  }

  Object.assign(definitions, {
    toggleToolActiveToolbar: { commandFn: actions.toggleToolActiveToolbar, context: 'CORNERSTONE' },
    getSegmentMeasurementVisibility: {
      commandFn: actions.getSegmentMeasurementVisibility,
      context: 'CORNERSTONE',
    },
    toggleSegmentMeasurement: { commandFn: actions.toggleSegmentMeasurement, context: 'CORNERSTONE' },
    toggleSegmentationVisibilityAllViewports: {
      commandFn: actions.toggleSegmentationVisibilityAllViewports,
      context: 'CORNERSTONE',
    },
    removeSegmentationFromViewport: {
      commandFn: actions.removeSegmentationFromViewport,
      context: 'CORNERSTONE',
    },
    downloadNninterSegmentation: {
      commandFn: actions.downloadNninterSegmentation,
      context: 'SEGMENTATION',
    },
    storeNninterSegmentation: {
      commandFn: actions.storeNninterSegmentation,
      context: 'SEGMENTATION',
    },
  });

  return { actions, definitions, defaultContext: 'DEFAULT' };
};

export default commandsModule;
