// Thin command layer. Every command delegates to a small model module — the command
// module owns no data model, no server bookkeeping, and no viewport internals.
//
// See docs/nninteractive-ohif-ideal-architecture.md §6 (Commands) and §16 (module map).

import { BaseVolumeViewport, VolumeViewport3D, eventTarget } from '@cornerstonejs/core';
import { Enums as csToolsEnums } from '@cornerstonejs/tools';

import * as sessionModel from './model/sessionModel';
import * as serverApi from './model/serverApi';
import * as objectModel from './model/objectModel';
import * as promptModel from './model/promptModel';
import * as coord from './model/coordinateMapping';
import * as bridge from './model/segmentationBridge';
import { debugSnapshot, installDebugHook } from './model/debugTools';
import { emptyPromptArrays, objectKeyOf } from './model/types';
import { toolboxState } from './utils/toolboxState';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;

// Guard so the MPR/brush event subscriptions are installed only once, even if
// getCommandsModule is ever invoked more than once.
let subscriptionsInstalled = false;

const commandsModule = ({ servicesManager, commandsManager }: any) => {
  const services = servicesManager.services;
  const {
    viewportGridService,
    cornerstoneViewportService,
    segmentationService,
    uiNotificationService,
  } = services;

  const notify = (message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') =>
    uiNotificationService?.show?.({ title: 'nnInteractive', message, type });

  const activeViewport = () => {
    const id = viewportGridService.getActiveViewportId?.();
    return id ? cornerstoneViewportService.getCornerstoneViewport(id) : undefined;
  };

  installDebugHook(servicesManager);

  async function setActiveObject(segmentationId: string, segmentIndex: number) {
    try {
      const viewportId = viewportGridService.getActiveViewportId?.();
      if (viewportId) {
        segmentationService.setActiveSegmentation?.(viewportId, segmentationId);
      }
    } catch {
      // ignore — the segment set below still targets the right segmentation
    }
    try {
      segmentationService.setActiveSegment?.(segmentationId, segmentIndex);
    } catch {
      // ignore
    }
    toolboxState.setCurrentActiveSegment(segmentIndex);
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
      target = active as { segmentationId: string; segmentIndex: number };
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
        const l = coord.freehandIJK(viewport, annotation, source.imageIds);
        if (!l) {
          continue;
        }
        (neg ? arrays.neg_lassos : arrays.pos_lassos).push(l);
      } else if (kind === 'scribble') {
        const s = coord.freehandIJK(viewport, annotation, source.imageIds);
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
      await bridge.clearSegment(servicesManager, segmentationId, segmentIndex);
      promptModel.clearForObject(objectKeyOf(segmentationId, segmentIndex));
      objectModel.markEmpty(segmentationId, segmentIndex);
      if (objectModel.holdsObject(segmentationId, segmentIndex)) {
        await actions.resetNninter();
      }
    },

    async deleteSegment({ segmentationId, segmentIndex }: any) {
      const held = objectModel.holdsObject(segmentationId, segmentIndex);
      await bridge.removeSegment(servicesManager, segmentationId, segmentIndex);
      promptModel.clearForObject(objectKeyOf(segmentationId, segmentIndex));
      objectModel.forgetObject(segmentationId, segmentIndex);
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
      await setActiveObject(segmentationId, segmentIndex);
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
        const resetFirst = await ensureBackendHoldsObject(source, segmentationId, segmentIndex, false);
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

    /** Export the nnInteractive segmentation to DICOM SEG (native OHIF multi-segment SEG). */
    async storeNninterSegmentation(args: any) {
      for (const segId of bridge.getManagedSegmentationIds()) {
        bridge.flushAuthoritativeLabelmap(servicesManager, segId, 'volumeToStack');
      }
      return commandsManager.run('storeSegmentation', args);
    },

    async downloadNninterSegmentation(args: any) {
      for (const segId of bridge.getManagedSegmentationIds()) {
        bridge.flushAuthoritativeLabelmap(servicesManager, segId, 'volumeToStack');
      }
      return commandsManager.run('downloadSegmentation', args);
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
