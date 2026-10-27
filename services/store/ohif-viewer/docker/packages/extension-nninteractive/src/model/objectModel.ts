// objectModel: maps OHIF segments to nnInteractive objects and tracks which object
// the backend currently holds, plus per-object dirty state.
//
// The active object is NOT a plugin singleton — it is the active OHIF segment. This
// module only derives that identity and records server-sync bookkeeping OHIF does not
// know about (which object the backend loaded, whether the local mask diverged, and
// whether an undo is currently safe).

import { ObjectRef, objectKeyOf } from './types';

// The object the backend session currently holds.
let serverObjectKey: string | undefined;
// True only when at least one prompt has been applied since the last init/reset/set_mask.
let undoableSinceLoad = false;
// Objects whose local mask changed (brush) since the last server sync.
const dirtyObjects = new Set<string>();
// Objects known to have no voxels. This lets the first prompt on a just-created
// empty segment skip a full labelmap scan before hitting the backend.
const knownEmptyObjects = new Set<string>();

/** The active nnInteractive object = the active OHIF segment in the active viewport. */
export function getActiveObject(servicesManager: any): ObjectRef | null {
  const { segmentationService, viewportGridService } = servicesManager.services;
  const viewportId = viewportGridService.getActiveViewportId();
  const activeSeg = segmentationService.getActiveSegmentation(viewportId);
  if (!activeSeg?.segmentationId) {
    return null;
  }
  const segmentIndex =
    segmentationService.getActiveSegment(viewportId)?.segmentIndex ??
    activeSeg.activeSegmentIndex ??
    1;
  return { segmentationId: activeSeg.segmentationId, segmentIndex };
}

export function getServerObject(): string | undefined {
  return serverObjectKey;
}

export function setServerObject(object: ObjectRef): void {
  serverObjectKey = objectKeyOf(object);
}

export function holdsObject(object: ObjectRef): boolean {
  return serverObjectKey === objectKeyOf(object);
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

export function markDirty(object: ObjectRef): void {
  const key = objectKeyOf(object);
  dirtyObjects.add(key);
  knownEmptyObjects.delete(key);
}

export function isDirty(object: ObjectRef): boolean {
  return dirtyObjects.has(objectKeyOf(object));
}

export function clearDirty(object: ObjectRef): void {
  dirtyObjects.delete(objectKeyOf(object));
}

export function markEmpty(object: ObjectRef): void {
  const key = objectKeyOf(object);
  knownEmptyObjects.add(key);
  dirtyObjects.delete(key);
}

export function markNonEmpty(object: ObjectRef): void {
  knownEmptyObjects.delete(objectKeyOf(object));
}

export function isKnownEmpty(object: ObjectRef): boolean {
  return knownEmptyObjects.has(objectKeyOf(object));
}

export function forgetObject(object: ObjectRef): void {
  const key = objectKeyOf(object);
  dirtyObjects.delete(key);
  knownEmptyObjects.delete(key);
  if (serverObjectKey === key) {
    clearServerObject();
  }
}

/** An object moved to another layer (new segmentation/index): carry its bookkeeping over. */
export function renameObject(from: ObjectRef, to: ObjectRef): void {
  const fromKey = objectKeyOf(from);
  const toKey = objectKeyOf(to);
  if (fromKey === toKey) {
    return;
  }
  if (serverObjectKey === fromKey) {
    serverObjectKey = toKey;
  }
  for (const set of [dirtyObjects, knownEmptyObjects]) {
    if (set.delete(fromKey)) {
      set.add(toKey);
    }
  }
}
