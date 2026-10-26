// debugTools: compact snapshots of nnInteractive/OHIF runtime state, for answering
// "which object is active, which mask does the server hold, which response is stale,
// and what did Cornerstone attach to each viewport?" without spelunking minified bundles.

import { cache } from '@cornerstonejs/core';
import {
  Enums as csToolsEnums,
  segmentation as csToolsSegmentation,
} from '@cornerstonejs/tools';
import { getActiveSource } from './imageModel';
import * as objectModel from './objectModel';
import * as promptModel from './promptModel';
import { sessionState } from './sessionModel';
import { viewportKind } from './coordinateMapping';
import { objectKeyOf } from './types';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;
export const DEBUG_HOOK_VERSION = 'nninteractive-services-v1';
let debugHookLogged = false;
let pendingHookLogged = false;

function callSafely<T>(fn: () => T): T | string | undefined {
  try {
    return fn();
  } catch (error) {
    return `ERR ${(error as Error)?.message ?? error}`;
  }
}

function hasCachedVolume(volumeId: unknown): boolean {
  if (typeof volumeId !== 'string' || !volumeId) {
    return false;
  }
  try {
    return !!cache.getVolume(volumeId);
  } catch {
    return false;
  }
}

function viewportSnapshot(servicesManager: any, viewportId: string): Record<string, any> {
  const { cornerstoneViewportService, segmentationService, viewportGridService } =
    servicesManager?.services ?? {};
  const gridViewport = viewportGridService?.getViewportState?.(viewportId);
  const viewportResult = callSafely(() =>
    cornerstoneViewportService?.getCornerstoneViewport?.(viewportId)
  ) as any;
  const viewportError = typeof viewportResult === 'string' ? viewportResult : undefined;
  const viewport = viewportError ? undefined : viewportResult;
  const volumeId = viewport ? callSafely(() => viewport.getVolumeId?.()) : undefined;
  const imageId = viewport ? callSafely(() => viewport.getCurrentImageId?.()) : undefined;
  const currentImageIndex = viewport ? callSafely(() => viewport.getCurrentImageIdIndex?.()) : undefined;
  const actors = viewport
    ? callSafely(() =>
        viewport.getActors?.()?.map((actorEntry: any) => ({
          uid: actorEntry.uid,
          referencedId: actorEntry.referencedId,
          representationUID: actorEntry.representationUID,
          className: actorEntry.actor?.getClassName?.(),
        }))
      )
    : undefined;
  const reps = callSafely(() =>
    segmentationService?.getSegmentationRepresentations?.(viewportId)?.map((rep: any) => ({
      segmentationId: rep.segmentationId,
      type: rep.type,
      active: rep.active,
      visible: rep.visible,
    }))
  );

  return {
    id: viewportId,
    found: !!viewport,
    error: viewportError,
    kind: viewportKind(viewport),
    viewportType: viewport?.type,
    grid: gridViewport
      ? {
          displaySetInstanceUIDs: gridViewport.displaySetInstanceUIDs,
          viewportType: gridViewport.viewportOptions?.viewportType,
          isReady: gridViewport.isReady,
        }
      : undefined,
    volumeId,
    hasVolume: hasCachedVolume(volumeId),
    imageId,
    currentImageIndex,
    actors,
    reps,
  };
}

function segmentationSnapshot(servicesManager: any): Record<string, any>[] {
  const service = servicesManager?.services?.segmentationService;
  const segmentations =
    callSafely(() => service?.getSegmentations?.()) ||
    callSafely(() => csToolsSegmentation.state.getSegmentations?.()) ||
    [];

  if (!Array.isArray(segmentations)) {
    return [{ error: segmentations }];
  }

  return segmentations.map((seg: any) => {
    const lm = seg?.representationData?.[LABELMAP];
    const nativeVolumeId = lm?.volumeId;
    return {
      segmentationId: seg.segmentationId,
      label: seg.label,
      cachedStats: seg.cachedStats,
      segmentKeys: Object.keys(seg.segments ?? {}),
      segments: Object.fromEntries(
        Object.entries(seg.segments ?? {}).map(([key, segment]: [string, any]) => [
          key,
          {
            label: segment?.label,
            active: segment?.active,
            locked: segment?.locked,
            cachedStats: segment?.cachedStats,
          },
        ])
      ),
      labelmap: {
        imageIds: lm?.imageIds?.length,
        referencedImageIds: lm?.referencedImageIds?.length,
        referencedVolumeId: lm?.referencedVolumeId,
        referencedVolumeCached: hasCachedVolume(lm?.referencedVolumeId),
        volumeId: nativeVolumeId,
        volumeCached: hasCachedVolume(nativeVolumeId),
      },
    };
  });
}

export function debugSnapshot(servicesManager: any): Record<string, any> {
  const { viewportGridService, cornerstoneViewportService } = servicesManager?.services ?? {};
  const viewportId = viewportGridService?.getActiveViewportId?.();
  const viewport = viewportId
    ? cornerstoneViewportService?.getCornerstoneViewport?.(viewportId)
    : undefined;
  const active = objectModel.getActiveObject(servicesManager);
  const activeKey = active ? objectKeyOf(active.segmentationId, active.segmentIndex) : undefined;

  const snapshot = {
    debugHook: DEBUG_HOOK_VERSION,
    ready: true,
    time: new Date().toISOString(),
    session: sessionState.get(),
    source: getActiveSource(servicesManager),
    viewport: {
      id: viewportId,
      kind: viewportKind(viewport),
    },
    viewportIds: cornerstoneViewportService?.getViewportIds?.() ?? [],
    viewports: (cornerstoneViewportService?.getViewportIds?.() ?? []).map((id: string) =>
      viewportSnapshot(servicesManager, id)
    ),
    segmentations: segmentationSnapshot(servicesManager),
    activeObject: active,
    serverObject: objectModel.getServerObject(),
    serverHoldsActive:
      !!active && objectModel.holdsObject(active.segmentationId, active.segmentIndex),
    undoable: objectModel.isUndoable(),
    prompts: activeKey ? promptModel.countForObject(activeKey) : { pending: 0, submitted: 0 },
  };

  // eslint-disable-next-line no-console
  console.info('[nninteractive] snapshot', snapshot);
  return snapshot;
}

export function installPendingDebugHook(): void {
  if (typeof globalThis === 'undefined') {
    return;
  }
  const existingVersion = (globalThis as any).__nnInteractiveDbgVersion;
  const existingReady = (globalThis as any).__nnInteractiveDbgReady;
  if (existingVersion === DEBUG_HOOK_VERSION && existingReady === true) {
    return;
  }

  const pendingHook = () => {
    const snapshot = {
      debugHook: DEBUG_HOOK_VERSION,
      ready: false,
      time: new Date().toISOString(),
      status: 'extension-loaded-services-not-bound',
    };
    // eslint-disable-next-line no-console
    console.info('[nninteractive] snapshot pending', snapshot);
    return snapshot;
  };

  (globalThis as any).__nnDbg = pendingHook;
  (globalThis as any).__nnInteractiveDbg = pendingHook;
  (globalThis as any).__nnInteractiveDbgVersion = DEBUG_HOOK_VERSION;
  (globalThis as any).__nnInteractiveDbgReady = false;
  if (!pendingHookLogged) {
    pendingHookLogged = true;
    console.info(
      `[nninteractive] debug hook pending: window.__nnInteractiveDbg() ${DEBUG_HOOK_VERSION}`
    );
  }
}

export function installDebugHook(servicesManager: any): void {
  if (typeof globalThis === 'undefined') {
    return;
  }
  const debugHook = () => debugSnapshot(servicesManager);
  (globalThis as any).__nnDbg = debugHook;
  (globalThis as any).__nnInteractiveDbg = debugHook;
  (globalThis as any).__nnInteractiveDbgVersion = DEBUG_HOOK_VERSION;
  (globalThis as any).__nnInteractiveDbgReady = true;
  if (!debugHookLogged) {
    debugHookLogged = true;
    console.info(
      `[nninteractive] debug hook installed: window.__nnInteractiveDbg() ${DEBUG_HOOK_VERSION}`
    );
  }
}
