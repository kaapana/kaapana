// imageModel: resolve the source image identity (series/study/display-set + image-id
// order) for the active viewport. Derived from OHIF display sets and viewport services;
// owns no pixels. Coordinate conversion and server init read the SourceImage from here.

import { SourceImage } from './types';

function readViewportDisplaySetUIDs(viewportGridService: any, viewportId: string): string[] {
  const state = viewportGridService?.getState?.();
  const viewports = state?.viewports;
  const vp = viewports?.get ? viewports.get(viewportId) : viewports?.[viewportId];
  if (!vp) {
    return [];
  }
  if (Array.isArray(vp.displaySetInstanceUIDs) && vp.displaySetInstanceUIDs.length) {
    return vp.displaySetInstanceUIDs;
  }
  if (Array.isArray(vp.displaySetOptions)) {
    return vp.displaySetOptions.map((o: any) => o?.displaySetInstanceUID).filter(Boolean);
  }
  return [];
}

function toSourceImage(displaySet: any): SourceImage | null {
  if (!displaySet?.SeriesInstanceUID || !displaySet?.StudyInstanceUID) {
    return null;
  }
  return {
    studyInstanceUID: displaySet.StudyInstanceUID,
    seriesInstanceUID: displaySet.SeriesInstanceUID,
    displaySetInstanceUID: displaySet.displaySetInstanceUID,
    imageIds: Array.isArray(displaySet.imageIds) ? displaySet.imageIds : [],
    seriesDescription: displaySet.SeriesDescription,
  };
}

/**
 * The source image series the active viewport is displaying. Prefers the display
 * set attached to the active viewport; falls back to the first reconstructable
 * active display set.
 */
export function getActiveSource(servicesManager: any): SourceImage | null {
  const { viewportGridService, displaySetService } = servicesManager?.services ?? {};
  if (!viewportGridService || !displaySetService) {
    return null;
  }

  const viewportId = viewportGridService.getActiveViewportId?.();
  const uids = viewportId ? readViewportDisplaySetUIDs(viewportGridService, viewportId) : [];
  const fromViewport = uids
    .map((uid: string) => displaySetService.getDisplaySetByUID?.(uid))
    .filter(Boolean);
  const imageDisplaySet =
    fromViewport.find((ds: any) => Array.isArray(ds.imageIds) && ds.imageIds.length) ??
    fromViewport[0];
  const fromViewportSource = imageDisplaySet ? toSourceImage(imageDisplaySet) : null;
  if (fromViewportSource?.imageIds.length) {
    return fromViewportSource;
  }

  // Fallback: any active display set that carries image ids.
  const active = displaySetService.activeDisplaySets ?? [];
  const fallback = active.find((ds: any) => Array.isArray(ds.imageIds) && ds.imageIds.length);
  return fallback ? toSourceImage(fallback) : fromViewportSource;
}

export function sameSource(a: SourceImage | null, b: SourceImage | null): boolean {
  return (
    !!a &&
    !!b &&
    a.studyInstanceUID === b.studyInstanceUID &&
    a.seriesInstanceUID === b.seriesInstanceUID
  );
}
