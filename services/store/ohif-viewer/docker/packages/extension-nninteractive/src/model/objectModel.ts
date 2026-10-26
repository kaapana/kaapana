// objectModel: maps OHIF segments to nnInteractive objects and tracks which object
// the backend currently holds, plus per-object dirty state.
//
// The active object is NOT a plugin singleton — it is the active OHIF segment. This
// module only derives that identity and records server-sync bookkeeping OHIF does not
// know about (which object the backend loaded, whether the local mask diverged, and
// whether an undo is currently safe).

import { objectKeyOf } from './types';

export interface ActiveObject {
  segmentationId: string;
  segmentIndex: number;
}

// The object the backend session currently holds, `${segmentationId}#${segmentIndex}`.
let serverObjectKey: string | undefined;
// True only when at least one prompt has been applied since the last init/reset/set_mask.
let undoableSinceLoad = false;
// Objects whose local mask changed (brush) since the last server sync.
const dirtyObjects = new Set<string>();
// Objects known to have no voxels. This lets the first prompt on a just-created
// empty segment skip a full labelmap scan before hitting the backend.
const knownEmptyObjects = new Set<string>();

/** The active nnInteractive object = the active OHIF segment in the active viewport. */
export function getActiveObject(servicesManager: any): ActiveObject | null {
  const service = servicesManager?.services?.segmentationService;
  const viewportGridService = servicesManager?.services?.viewportGridService;
  if (!service) {
    return null;
  }
  const viewportId = viewportGridService?.getActiveViewportId?.();
  const activeSeg = service.getActiveSegmentation?.(viewportId);
  if (!activeSeg?.segmentationId) {
    return null;
  }
  const activeSegment = service.getActiveSegment?.(viewportId);
  const segmentIndex =
    activeSegment?.segmentIndex ?? activeSeg.activeSegmentIndex ?? 1;
  return { segmentationId: activeSeg.segmentationId, segmentIndex };
}

export function objectKey(segmentationId: string, segmentIndex: number): string {
  return objectKeyOf(segmentationId, segmentIndex);
}

export function getServerObject(): string | undefined {
  return serverObjectKey;
}

export function setServerObject(segmentationId: string, segmentIndex: number): void {
  serverObjectKey = objectKeyOf(segmentationId, segmentIndex);
}

export function holdsObject(segmentationId: string, segmentIndex: number): boolean {
  return serverObjectKey === objectKeyOf(segmentationId, segmentIndex);
}

export function clearServerObject(): void {
  serverObjectKey = undefined;
  undoableSinceLoad = false;
}

export function setUndoable(value: boolean): void {
  undoableSinceLoad = value;
}

export function isUndoable(): boolean {
  return undoableSinceLoad;
}

export function markDirty(segmentationId: string, segmentIndex: number): void {
  const key = objectKeyOf(segmentationId, segmentIndex);
  dirtyObjects.add(key);
  knownEmptyObjects.delete(key);
}

export function isDirty(segmentationId: string, segmentIndex: number): boolean {
  return dirtyObjects.has(objectKeyOf(segmentationId, segmentIndex));
}

export function clearDirty(segmentationId: string, segmentIndex: number): void {
  dirtyObjects.delete(objectKeyOf(segmentationId, segmentIndex));
}

export function markEmpty(segmentationId: string, segmentIndex: number): void {
  const key = objectKeyOf(segmentationId, segmentIndex);
  knownEmptyObjects.add(key);
  dirtyObjects.delete(key);
}

export function markNonEmpty(segmentationId: string, segmentIndex: number): void {
  knownEmptyObjects.delete(objectKeyOf(segmentationId, segmentIndex));
}

export function isKnownEmpty(segmentationId: string, segmentIndex: number): boolean {
  return knownEmptyObjects.has(objectKeyOf(segmentationId, segmentIndex));
}

export function forgetObject(segmentationId: string, segmentIndex: number): void {
  const key = objectKeyOf(segmentationId, segmentIndex);
  dirtyObjects.delete(key);
  knownEmptyObjects.delete(key);
  if (serverObjectKey === key) {
    clearServerObject();
  }
}
