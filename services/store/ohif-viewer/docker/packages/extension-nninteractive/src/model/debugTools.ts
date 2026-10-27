// debugTools: compact snapshots of nnInteractive/OHIF runtime state, for answering
// "which object is active, which mask does the server hold, which response is stale,
// and what did Cornerstone attach to each viewport?" without spelunking minified bundles.

import { cache, setPreferSizeOverAccuracy } from '@cornerstonejs/core';
import { Enums as csToolsEnums, segmentation as csToolsSegmentation } from '@cornerstonejs/tools';

import { getActiveSource } from './imageModel';
import * as objectModel from './objectModel';
import * as promptModel from './promptModel';
import { sessionState } from './sessionModel';
import { viewportKind } from './coordinateMapping';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;

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
  const currentImageIndex = viewport
    ? callSafely(() => viewport.getCurrentImageIdIndex?.())
    : undefined;
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

function debugSnapshot(servicesManager: any): Record<string, any> {
  const { viewportGridService, cornerstoneViewportService } = servicesManager.services;
  const viewportId = viewportGridService.getActiveViewportId();
  const viewport = viewportId
    ? cornerstoneViewportService.getCornerstoneViewport(viewportId)
    : undefined;
  const active = objectModel.getActiveObject(servicesManager);

  const snapshot = {
    time: new Date().toISOString(),
    session: sessionState.get(),
    source: getActiveSource(servicesManager),
    viewport: { id: viewportId, kind: viewportKind(viewport) },
    viewports: cornerstoneViewportService
      .getViewportIds()
      .map((id: string) => viewportSnapshot(servicesManager, id)),
    segmentations: segmentationSnapshot(servicesManager),
    activeObject: active,
    serverObject: objectModel.getServerObject(),
    serverHoldsActive: !!active && objectModel.holdsObject(active),
    undoable: objectModel.isUndoable(),
    prompts: active ? promptModel.countForObject(active) : { pending: 0, submitted: 0 },
  };

  console.info('[nninteractive] snapshot', snapshot);
  return snapshot;
}

/** What the GPU reports for the texture formats Cornerstone uses for volumes (MPR). */
function gpuInfo() {
  const gl = document.createElement('canvas').getContext('webgl2');
  if (!gl) {
    return { webgl2: false };
  }
  const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
  return {
    webgl2: true,
    renderer: debugInfo
      ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
      : gl.getParameter(gl.RENDERER),
    vendor: debugInfo
      ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)
      : gl.getParameter(gl.VENDOR),
    norm16: !!gl.getExtension('EXT_texture_norm16'),
    floatLinear: !!gl.getExtension('OES_texture_float_linear'),
    max3DTextureSize: gl.getParameter(gl.MAX_3D_TEXTURE_SIZE),
  };
}

/**
 * Console hooks: `__nnInteractiveDbg()` logs and returns a runtime snapshot. GPU diagnostics for
 * black volume (MPR) viewports: `__nnInteractiveGpu.info()`, and
 * `__nnInteractiveGpu.preferSize(true)` before opening MPR to skip 16-bit-normalized textures.
 */
export function installDebugHook(servicesManager: any): void {
  Object.assign(globalThis, {
    __nnInteractiveDbg: () => debugSnapshot(servicesManager),
    __nnInteractiveGpu: {
      info: gpuInfo,
      preferSize: (on = true) => setPreferSizeOverAccuracy(on),
    },
  });
}
