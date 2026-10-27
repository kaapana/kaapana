// segmentationBridge: the only module that reads or writes native OHIF/Cornerstone
// segmentation labelmap data.
//
// Data model: nnInteractive objects are SEGMENTS packed into as few OHIF segmentations
// ("layers") as possible. A layer is an ordinary single-labelmap segmentation; each object
// owns one segment index there and its voxels hold that index. Objects of one layer cannot
// share voxels, so an object whose mask would overlap another object of its layer is moved
// to a layer where it fits (or to a new layer). A typical session needs a single layer, so
// memory and render cost grow with the number of OVERLAPPING objects, not with the number
// of objects. An object's identity `${segmentationId}#${segmentIndex}` therefore changes
// when it moves; applyCrop reports the new location and the caller re-keys its bookkeeping.
//
// Storage: a layer's stack labelmap images (one derived image per source image) are the
// only voxel store. Cornerstone 5 renders the same images in stack viewports and, through
// an image-backed geometry volume, in MPR viewports — so a write here (or a brush stroke in
// either view) is visible everywhere after triggerSegmentationDataModified.
//
// (Cornerstone's own multi-layer labelmaps — `labelmaps`/`segmentBindings` — would do the
// packing natively, but in OHIF's legacy viewports a second layer switches the labelmap to
// slice-actor rendering, which drops label value 1 on every layer. One labelmap per
// segmentation stays on the well-trodden rendering path.)

import {
  cache,
  metaData,
  utilities as csUtils,
  BaseVolumeViewport,
  VolumeViewport3D,
} from '@cornerstonejs/core';
import { Enums as csToolsEnums, segmentation as csToolsSegmentation } from '@cornerstonejs/tools';

import { ObjectRef, PredictionCrop, SourceImage } from './types';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;
// Labelmap images are Uint8: values 2..255 are object segment indices. Value 1 is never used:
// vtk.js's 2D label-outline shader (stack viewports) computes `int(texel * 255.0)`, which
// truncates 1/255*255 to 0 and draws label 1 as background — no fill, no outline.
const FIRST_OBJECT_INDEX = 2;
const MAX_OBJECTS_PER_LAYER = 255;

// nnInteractive layer segmentations grouped by source series.
const managedSegIdsBySeries = new Map<string, Set<string>>();
// Layer segmentations this module created (so import logic never re-processes them).
const managedSegIds = new Set<string>();
// Externally-hydrated segmentations already split into objects. Their state is KEPT
// (deleting it crashes OHIF's presentation store / toolbar evaluators); a later rep re-add
// (viewport remount, re-hydration of the same SEG) is just re-stripped, never re-split.
const splitConsumedIds = new Set<string>();
// Reentrancy guard while a split runs for one hydrated segmentation.
const splitInProgress = new Set<string>();

export interface ApplyCropResult {
  /** The object's location after the write; differs from the target when it was moved. */
  object: ObjectRef;
  moved: boolean;
  wroteVoxels: boolean;
}

/** An object mask restricted to the slices it occupies: z → binary slice (rows*columns). */
type SliceMasks = Map<number, Uint8Array>;

interface ObjectMeta {
  label: string;
  color: number[];
  objectOrdinal: number;
}

// Distinct object colors (RGBA 0-255), assigned by object ordinal.
const OBJECT_COLORS: number[][] = [
  [230, 25, 75, 255],
  [60, 180, 75, 255],
  [0, 130, 200, 255],
  [245, 130, 48, 255],
  [145, 30, 180, 255],
  [70, 240, 240, 255],
  [240, 50, 230, 255],
  [210, 245, 60, 255],
  [250, 190, 190, 255],
  [0, 128, 128, 255],
];

export function objectColorForOrdinal(ordinal: number): number[] {
  return OBJECT_COLORS[Math.max(0, ordinal - 1) % OBJECT_COLORS.length];
}

export function isManaged(segmentationId: string): boolean {
  if (managedSegIds.has(segmentationId)) {
    return true;
  }
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  if (isTaggedManagedSegmentation(seg)) {
    registerManagedSegmentation(
      segmentationId,
      getSeriesInstanceUIDForSegmentation(segmentationId)
    );
    return true;
  }
  return false;
}

function isTaggedManagedSegmentation(seg: any): boolean {
  return seg?.cachedStats?.nninteractiveManaged === true;
}

function registerManagedSegmentation(segmentationId: string, seriesInstanceUID?: string): void {
  managedSegIds.add(segmentationId);
  if (!seriesInstanceUID) {
    return;
  }
  let ids = managedSegIdsBySeries.get(seriesInstanceUID);
  if (!ids) {
    ids = new Set<string>();
    managedSegIdsBySeries.set(seriesInstanceUID, ids);
  }
  ids.add(segmentationId);
}

function unregisterManagedSegmentation(segmentationId: string): void {
  managedSegIds.delete(segmentationId);
  for (const ids of managedSegIdsBySeries.values()) {
    ids.delete(segmentationId);
  }
}

export function getSeriesInstanceUIDForSegmentation(segmentationId: string): string | undefined {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const value = seg?.cachedStats?.seriesInstanceUid;
  return typeof value === 'string' && value ? value : undefined;
}

function getLayerOrdinal(segmentationId: string): number {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const ordinal = Number(seg?.cachedStats?.layerOrdinal);
  return Number.isInteger(ordinal) && ordinal > 0 ? ordinal : Number.MAX_SAFE_INTEGER;
}

function byLayerOrdinal(a: string, b: string): number {
  return getLayerOrdinal(a) - getLayerOrdinal(b) || a.localeCompare(b);
}

/** Layer segmentations of a series, in creation order. */
function getManagedSegmentationIdsForSeries(seriesInstanceUID: string): string[] {
  const ids = new Set<string>(managedSegIdsBySeries.get(seriesInstanceUID) ?? []);

  // Recover after a state reset by scanning for managed segmentations tagged with the series.
  const all = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];
  for (const seg of all) {
    if (
      isTaggedManagedSegmentation(seg) &&
      seg?.cachedStats?.seriesInstanceUid === seriesInstanceUID
    ) {
      registerManagedSegmentation(seg.segmentationId, seriesInstanceUID);
      ids.add(seg.segmentationId);
    }
  }

  return Array.from(ids)
    .filter(segmentationId => !!csToolsSegmentation.state.getSegmentation(segmentationId))
    .sort(byLayerOrdinal);
}

/** All layer segmentations, in creation order. */
function getManagedSegmentationIds(): string[] {
  const all = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];
  for (const seg of all) {
    if (isTaggedManagedSegmentation(seg)) {
      registerManagedSegmentation(seg.segmentationId, seg?.cachedStats?.seriesInstanceUid);
    }
  }
  return Array.from(managedSegIds)
    .filter(segmentationId => !!csToolsSegmentation.state.getSegmentation(segmentationId))
    .sort(byLayerOrdinal);
}

function segmentIndicesOf(segmentationId: string): number[] {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  return Object.keys(seg?.segments ?? {})
    .map(Number)
    .filter(n => Number.isInteger(n) && n > 0)
    .sort((a, b) => a - b);
}

function getObjectOrdinal(object: ObjectRef): number {
  const ordinal = Number(
    getSegment(object.segmentationId, object.segmentIndex)?.cachedStats?.objectOrdinal
  );
  return Number.isInteger(ordinal) && ordinal > 0 ? ordinal : Number.MAX_SAFE_INTEGER;
}

function objectsOfLayers(layerIds: string[]): ObjectRef[] {
  return layerIds
    .flatMap(segmentationId =>
      segmentIndicesOf(segmentationId).map(segmentIndex => ({ segmentationId, segmentIndex }))
    )
    .sort((a, b) => getObjectOrdinal(a) - getObjectOrdinal(b));
}

/** Every object of a series, in creation (ordinal) order. */
export function getObjectsForSeries(seriesInstanceUID: string): ObjectRef[] {
  return objectsOfLayers(getManagedSegmentationIdsForSeries(seriesInstanceUID));
}

/** Every object of every series, in creation (ordinal) order. */
export function getObjects(): ObjectRef[] {
  return objectsOfLayers(getManagedSegmentationIds());
}

function nextObjectOrdinal(seriesInstanceUID: string): number {
  const ordinals = getObjectsForSeries(seriesInstanceUID)
    .map(getObjectOrdinal)
    .filter(ordinal => ordinal < Number.MAX_SAFE_INTEGER);
  return ordinals.length ? Math.max(...ordinals) + 1 : 1;
}

function nextLayerOrdinal(seriesInstanceUID: string): number {
  const ordinals = getManagedSegmentationIdsForSeries(seriesInstanceUID)
    .map(getLayerOrdinal)
    .filter(ordinal => ordinal < Number.MAX_SAFE_INTEGER);
  return ordinals.length ? Math.max(...ordinals) + 1 : 1;
}

function dispatchModified(segmentationId: string): void {
  csToolsSegmentation.triggerSegmentationEvents.triggerSegmentationDataModified(segmentationId);
}

function failHard(message: string, detail?: unknown): never {
  if (detail !== undefined) {
    console.error(`[nninteractive] ${message}`, detail);
  } else {
    console.error(`[nninteractive] ${message}`);
  }
  throw new Error(`[nninteractive] ${message}`);
}

// ── Labelmap image access ───────────────────────────────────────────────────────────────────

/**
 * One layer's voxel store, indexed by display slice: `slices[z]` is the scalar array of the
 * labelmap image derived from source image `sourceImageIds[z]` (mutated in place — replacing
 * the array would detach it from the image's voxel manager).
 */
interface LabelmapContext {
  slices: (ArrayLike<number> & { [index: number]: number })[];
  rows: number;
  columns: number;
  sliceLen: number;
  sourceImageIds: string[];
}

function getSourceImageIdsForSegmentation(segmentationId: string): string[] {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const lm: any = seg?.representationData?.[LABELMAP];
  if (Array.isArray(lm?.referencedImageIds) && lm.referencedImageIds.length) {
    return lm.referencedImageIds;
  }
  const imageIds: string[] = lm?.imageIds ?? [];
  return imageIds
    .map(imageId => (cache.getImage(imageId) as any)?.referencedImageId)
    .filter(Boolean);
}

function getLabelmapContext(segmentationId: string): LabelmapContext | null {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const labelmapImageIds: string[] = (seg?.representationData?.[LABELMAP] as any)?.imageIds ?? [];
  const sourceImageIds = getSourceImageIdsForSegmentation(segmentationId);
  if (!labelmapImageIds.length || !sourceImageIds.length) {
    return null;
  }

  const labelmapImageIdByReference = new Map<string, string>();
  for (const imageId of labelmapImageIds) {
    const referencedImageId = (cache.getImage(imageId) as any)?.referencedImageId;
    if (referencedImageId && !labelmapImageIdByReference.has(referencedImageId)) {
      labelmapImageIdByReference.set(referencedImageId, imageId);
    }
  }

  let rows = 0;
  let columns = 0;
  const slices = sourceImageIds.map(sourceImageId => {
    const labelmapImageId = labelmapImageIdByReference.get(sourceImageId);
    const image: any = labelmapImageId ? cache.getImage(labelmapImageId) : undefined;
    const scalarData = image?.voxelManager?.getScalarData?.();
    if (!scalarData) {
      return null;
    }
    rows ||= image.rows;
    columns ||= image.columns;
    return scalarData.length === rows * columns ? scalarData : null;
  });
  if (!rows || !columns || slices.some(slice => !slice)) {
    return null;
  }
  return { slices, rows, columns, sliceLen: rows * columns, sourceImageIds };
}

function requireLabelmapContext(segmentationId: string): LabelmapContext {
  const ctx = getLabelmapContext(segmentationId);
  if (!ctx) {
    failHard(`labelmap images for segmentation ${segmentationId} are not cached`);
  }
  return ctx;
}

function clearValueFromSlice(
  slice: LabelmapContext['slices'][number],
  segmentIndex: number
): boolean {
  let changed = false;
  for (let j = 0; j < slice.length; j++) {
    if (slice[j] === segmentIndex) {
      slice[j] = 0;
      changed = true;
    }
  }
  return changed;
}

// ── Per-segment dirty-slice bookkeeping (lets clears touch only populated slices) ───────────

function getSegment(segmentationId: string, segmentIndex: number): any {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  return seg?.segments?.[segmentIndex];
}

function getSegmentDirtySlices(
  segmentationId: string,
  segmentIndex: number
): {
  known: boolean;
  slices: number[];
} {
  const stats = getSegment(segmentationId, segmentIndex)?.cachedStats;
  if (!stats || !Array.isArray(stats.dirtySlices)) {
    return { known: false, slices: [] };
  }
  return {
    known: true,
    slices: Array.from(
      new Set(
        stats.dirtySlices
          .map((slice: unknown) => Number(slice))
          .filter((slice: number) => Number.isInteger(slice) && slice >= 0)
      )
    ),
  };
}

/** Slices that may hold the object's voxels: the recorded dirty slices, else all. */
function candidateSlices(ctx: LabelmapContext, object: ObjectRef): number[] {
  const dirty = getSegmentDirtySlices(object.segmentationId, object.segmentIndex);
  return dirty.known
    ? dirty.slices.filter(z => z < ctx.slices.length)
    : ctx.slices.map((_, z) => z);
}

function updateSegmentDirtyStats(
  segmentationId: string,
  segmentIndex: number,
  dirtySlices: number[]
): void {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  if (!seg) {
    return;
  }
  const unique = Array.from(new Set(dirtySlices)).sort((a, b) => a - b);
  const segments = { ...(seg.segments ?? {}) };
  const segment = segments[segmentIndex] ?? ({ segmentIndex } as any);
  segments[segmentIndex] = {
    ...segment,
    cachedStats: { ...(segment.cachedStats ?? {}), dirtySlices: unique },
  };
  csToolsSegmentation.updateSegmentations([{ segmentationId, payload: { segments } }]);
}

// ── Viewport representations ────────────────────────────────────────────────────────────────

function classifyViewports(servicesManager: any): { planar: string[]; volume3d: string[] } {
  const cvs = servicesManager.services.cornerstoneViewportService;
  const planar: string[] = [];
  const volume3d: string[] = [];
  for (const viewportId of cvs.getViewportIds()) {
    const vp = cvs.getCornerstoneViewport(viewportId);
    if (vp instanceof VolumeViewport3D) {
      volume3d.push(viewportId);
    } else if (!(vp instanceof BaseVolumeViewport) || isVolumeViewportReady(vp)) {
      planar.push(viewportId);
    }
  }
  return { planar, volume3d };
}

function isVolumeViewportReady(viewport: any): boolean {
  try {
    const volumeId = viewport?.getVolumeId?.();
    return typeof volumeId === 'string' && !!volumeId && !!cache.getVolume(volumeId);
  } catch {
    return false;
  }
}

function getRepresentationsMissing(
  servicesManager: any,
  segmentationId: string,
  viewportIds: string[]
): string[] {
  const service = servicesManager.services.segmentationService;
  return viewportIds.filter(viewportId => {
    const reps =
      service.getSegmentationRepresentations(viewportId, {
        segmentationId,
        type: LABELMAP,
      }) ?? [];
    return !reps.some(
      (rep: any) => rep?.segmentationId === segmentationId && rep?.type === LABELMAP
    );
  });
}

function rgbMatches(a: unknown, b: unknown): boolean {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length < 3 || b.length < 3) {
    return false;
  }
  for (let i = 0; i < 3; i++) {
    if (Math.round(Number(a[i])) !== Math.round(Number(b[i]))) {
      return false;
    }
  }
  return true;
}

// Apply each object's palette color to its representation in the given viewports, but only
// where the representation's current color differs. Returns true if any color changed.
//
// This must re-check on every guard pass rather than run once at rep-add time: switching
// layout makes OHIF auto-propagate the labelmap representation into the new viewports, and
// those reps never appear as "missing". If we only colored freshly-added reps, every object
// would keep Cornerstone's default color for its segment index there — both the render and
// the panel (which reads the active viewport's representation color) would then be wrong.
function applySegmentColors(
  servicesManager: any,
  segmentationId: string,
  viewportIds: string[]
): boolean {
  const service: any = servicesManager.services.segmentationService;
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const segments = Object.values(seg?.segments ?? {}) as any[];
  let applied = false;
  for (const segment of segments) {
    const segmentIndex = Number(segment?.segmentIndex);
    const color = segment?.cachedStats?.color ?? segment?.color;
    if (!Number.isInteger(segmentIndex) || !Array.isArray(color)) {
      continue;
    }
    for (const viewportId of viewportIds) {
      let current: unknown;
      try {
        current = service.getSegmentColor(viewportId, segmentationId, segmentIndex);
      } catch {
        current = undefined;
      }
      if (rgbMatches(current, color)) {
        continue;
      }
      try {
        service.setSegmentColor(viewportId, segmentationId, segmentIndex, color);
        applied = true;
      } catch {
        // ignore — color is a display nicety
      }
    }
  }
  return applied;
}

function removeRepresentations(
  servicesManager: any,
  segmentationId: string,
  viewportIds: string[]
): void {
  const service = servicesManager.services.segmentationService;
  for (const viewportId of viewportIds) {
    if (!service.getSegmentationRepresentations(viewportId, { segmentationId })?.length) {
      continue;
    }
    try {
      service.removeRepresentationsFromViewport(viewportId, { segmentationId });
    } catch {
      // ignore — representation may already be gone
    }
  }
}

async function attachRepresentations(
  servicesManager: any,
  segmentationId: string
): Promise<boolean> {
  const service = servicesManager.services.segmentationService;
  const { planar, volume3d } = classifyViewports(servicesManager);
  const missing = getRepresentationsMissing(servicesManager, segmentationId, planar);
  for (const viewportId of missing) {
    try {
      await service.addSegmentationRepresentation(viewportId, { segmentationId });
    } catch (error) {
      failHard(`could not add representation for ${segmentationId} in ${viewportId}`, error);
    }
  }
  // Labelmap→surface in a 3D viewport crashes polySeg — never attach there.
  removeRepresentations(servicesManager, segmentationId, volume3d);
  const colored = applySegmentColors(servicesManager, segmentationId, planar);
  return missing.length > 0 || colored;
}

/**
 * Viewport guard: after a layout or viewport change, make every layer visible (with its
 * objects' colors) in each stack/MPR viewport and absent from 3D viewports. Cost scales with
 * the number of layers, not objects.
 */
export async function ensureViewportRepresentations(servicesManager: any): Promise<void> {
  for (const segmentationId of getManagedSegmentationIds()) {
    if (await attachRepresentations(servicesManager, segmentationId)) {
      dispatchModified(segmentationId);
    }
  }
}

/**
 * Brush/eraser edits must never overwrite another object that shares the active object's
 * layer: lock every object except the active one (Cornerstone's labelmap tools skip voxels
 * of locked segments). Only touches segments whose lock state differs.
 */
export function applyEditLocks(active: ObjectRef | null): void {
  const { segmentLocking } = csToolsSegmentation;
  for (const segmentationId of getManagedSegmentationIds()) {
    for (const segmentIndex of segmentIndicesOf(segmentationId)) {
      const locked = !(
        active &&
        active.segmentationId === segmentationId &&
        active.segmentIndex === segmentIndex
      );
      if (segmentLocking.isSegmentIndexLocked(segmentationId, segmentIndex) !== locked) {
        segmentLocking.setSegmentIndexLocked(segmentationId, segmentIndex, locked);
      }
    }
  }
}

// ── Layers ──────────────────────────────────────────────────────────────────────────────────

function sourceSliceGeometry(source: SourceImage): { rows: number; columns: number } {
  const imageId = source.imageIds[0];
  const image: any = imageId ? cache.getImage(imageId) : undefined;
  const pixelModule: any = imageId ? metaData.get('imagePixelModule', imageId) : undefined;
  return {
    rows: Number(image?.rows ?? pixelModule?.rows) || 0,
    columns: Number(image?.columns ?? pixelModule?.columns) || 0,
  };
}

const MB = 1024 * 1024;

/**
 * A layer is a full-size labelmap. Refuse to allocate one the Cornerstone cache cannot hold:
 * past its limit the derived images are silently not cached and every later write fails.
 */
function assertCacheRoomForLayer(source: SourceImage): void {
  const { rows, columns } = sourceSliceGeometry(source);
  const needed = rows * columns * source.imageIds.length;
  const free = cache.getMaxCacheSize() - cache.getCacheSize();
  if (needed && needed > free) {
    throw new Error(
      `Not enough viewer memory for another segmentation layer (needs ${Math.ceil(needed / MB)} MB, ` +
        `${Math.max(0, Math.floor(free / MB))} MB free). Delete objects you no longer need, ` +
        'or save and reload the viewer.'
    );
  }
}

function layerLabel(layerOrdinal: number): string {
  return layerOrdinal === 1
    ? 'nnInteractive objects'
    : `nnInteractive objects (layer ${layerOrdinal})`;
}

async function deleteLayer(commandsManager: any, segmentationId: string): Promise<void> {
  const labelmap: any =
    csToolsSegmentation.state.getSegmentation(segmentationId)?.representationData?.[LABELMAP];
  const imageIds: string[] = labelmap?.imageIds ?? [];
  try {
    await commandsManager.run('deleteSegmentation', { segmentationId });
  } finally {
    unregisterManagedSegmentation(segmentationId);
  }
  // Removing a segmentation leaves its labelmap images in the cache (~47 MB per layer for a
  // 512×512×178 CT); nothing else references a layer's images.
  for (const imageId of imageIds) {
    if (cache.getImage(imageId)) {
      cache.removeImageLoadObject(imageId, { force: true });
    }
  }
}

/** Create a new, empty layer segmentation for the source series. */
async function createLayer(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage
): Promise<string> {
  assertCacheRoomForLayer(source);
  const layerOrdinal = nextLayerOrdinal(source.seriesInstanceUID);
  const segmentationId = csUtils.uuidv4();
  // Not the `loadSegmentationsForViewport` command: it derives the labelmap from the active
  // viewport's first display set, which can be a SEG overlay (its labelmap images then become
  // the "source", and the layer has the wrong size and no CT references for export).
  const { segmentationService, displaySetService } = servicesManager.services;
  const displaySet = displaySetService.getDisplaySetByUID(source.displaySetInstanceUID);
  if (!displaySet) {
    failHard(`source display set ${source.displaySetInstanceUID} not found`);
  }
  try {
    await segmentationService.createLabelmapForDisplaySet(displaySet, {
      segmentationId,
      segments: {},
      label: layerLabel(layerOrdinal),
    });
  } catch (error) {
    failHard('createLabelmapForDisplaySet failed', error);
  }
  const created: any = csToolsSegmentation.state.getSegmentation(segmentationId);
  const imageIds: string[] = created?.representationData?.[LABELMAP]?.imageIds ?? [];
  if (!imageIds.length || imageIds.some(imageId => !cache.getImage(imageId))) {
    // Allocation hit the cache limit after all (other data grew meanwhile): undo it.
    if (created) {
      await deleteLayer(commandsManager, segmentationId).catch(() => undefined);
    }
    throw new Error(
      'Not enough viewer memory for another segmentation layer. Delete objects you no longer ' +
        'need, or save and reload the viewer.'
    );
  }

  csToolsSegmentation.updateSegmentations([
    {
      segmentationId,
      payload: {
        cachedStats: {
          ...(created.cachedStats ?? {}),
          nninteractiveManaged: true,
          seriesInstanceUid: source.seriesInstanceUID,
          displaySetInstanceUID: source.displaySetInstanceUID,
          layerOrdinal,
        },
      },
    },
  ]);
  registerManagedSegmentation(segmentationId, source.seriesInstanceUID);
  await attachRepresentations(servicesManager, segmentationId);
  // OHIF gives a segmentation created without segments a default "Segment 1"; a layer holds
  // only objects.
  for (const segmentIndex of segmentIndicesOf(segmentationId)) {
    removeSegmentEntry({ segmentationId, segmentIndex });
  }
  return segmentationId;
}

function freeSegmentIndex(segmentationId: string): number | undefined {
  const used = new Set(segmentIndicesOf(segmentationId));
  for (let index = FIRST_OBJECT_INDEX; index <= MAX_OBJECTS_PER_LAYER; index++) {
    if (!used.has(index)) {
      return index;
    }
  }
  return undefined;
}

/** True when none of the mask's voxels is taken in the layer. */
function maskFits(ctx: LabelmapContext, mask: SliceMasks): boolean {
  for (const [z, sliceMask] of mask) {
    const slice = ctx.slices[z];
    if (!slice) {
      return false;
    }
    for (let j = 0; j < sliceMask.length; j++) {
      if (sliceMask[j] && slice[j] !== 0) {
        return false;
      }
    }
  }
  return true;
}

/** The first layer of the series (in creation order) with a free index where `mask` fits. */
function findLayerFor(
  seriesInstanceUID: string,
  mask: SliceMasks,
  excludeSegmentationId?: string
): string | undefined {
  for (const segmentationId of getManagedSegmentationIdsForSeries(seriesInstanceUID)) {
    if (
      segmentationId === excludeSegmentationId ||
      freeSegmentIndex(segmentationId) === undefined
    ) {
      continue;
    }
    if (!mask.size) {
      return segmentationId;
    }
    const ctx = getLabelmapContext(segmentationId);
    if (ctx && maskFits(ctx, mask)) {
      return segmentationId;
    }
  }
  return undefined;
}

/**
 * Store an object with the given mask and metadata in a layer where it fits, creating a
 * layer if none does. Returns where it was placed.
 */
async function placeObject(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage,
  mask: SliceMasks,
  meta: ObjectMeta,
  excludeSegmentationId?: string
): Promise<ObjectRef> {
  const segmentationId =
    findLayerFor(source.seriesInstanceUID, mask, excludeSegmentationId) ??
    (await createLayer(servicesManager, commandsManager, source));
  const segmentIndex = freeSegmentIndex(segmentationId);
  if (segmentIndex === undefined) {
    failHard(`layer ${segmentationId} has no free segment index`);
  }

  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  csToolsSegmentation.updateSegmentations([
    {
      segmentationId,
      payload: {
        segments: {
          ...(seg?.segments ?? {}),
          [segmentIndex]: {
            segmentIndex,
            label: meta.label,
            color: meta.color,
            locked: false,
            active: false,
            cachedStats: { color: meta.color, objectOrdinal: meta.objectOrdinal, dirtySlices: [] },
          } as any,
        },
      },
    },
  ]);

  const written: number[] = [];
  if (mask.size) {
    const ctx = requireLabelmapContext(segmentationId);
    for (const [z, sliceMask] of mask) {
      const slice = ctx.slices[z];
      let wrote = false;
      for (let j = 0; j < sliceMask.length; j++) {
        if (sliceMask[j]) {
          slice[j] = segmentIndex;
          wrote = true;
        }
      }
      if (wrote) {
        written.push(z);
      }
    }
  }
  updateSegmentDirtyStats(segmentationId, segmentIndex, written);
  applySegmentColors(servicesManager, segmentationId, classifyViewports(servicesManager).planar);
  dispatchModified(segmentationId);
  return { segmentationId, segmentIndex };
}

function objectMeta(object: ObjectRef): ObjectMeta {
  const segment = getSegment(object.segmentationId, object.segmentIndex);
  const objectOrdinal = Number(segment?.cachedStats?.objectOrdinal) || 0;
  return {
    label: segment?.label || `Object ${objectOrdinal || object.segmentIndex}`,
    color:
      (Array.isArray(segment?.cachedStats?.color) && segment.cachedStats.color) ||
      (Array.isArray(segment?.color) && segment.color) ||
      objectColorForOrdinal(objectOrdinal || 1),
    objectOrdinal,
  };
}

/**
 * Drop a segment entry (voxels must already be cleared) without touching the active segment.
 * Mirrors cornerstone's removeSegment minus its clearSegmentValue, which re-clears the value
 * with a per-voxel callback over the whole layer (~2-3 s for a 512×512×178 CT).
 */
function removeSegmentEntry(object: ObjectRef): void {
  const { segmentationId, segmentIndex } = object;
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  if (!seg) {
    return;
  }
  const segments = { ...seg.segments };
  delete segments[segmentIndex];
  // Cornerstone re-creates a binding for every listed segment but never prunes stale ones.
  delete (seg.representationData?.Labelmap as any)?.segmentBindings?.[segmentIndex];
  csToolsSegmentation.updateSegmentations([{ segmentationId, payload: { segments } }]);
  for (const viewportId of csToolsSegmentation.state.getViewportIdsWithSegmentation(
    segmentationId
  )) {
    for (const rep of csToolsSegmentation.state.getSegmentationRepresentations(viewportId, {
      segmentationId,
    })) {
      delete (rep.segments as any)?.[segmentIndex];
    }
  }
  dispatchModified(segmentationId);
}

// ── Objects ─────────────────────────────────────────────────────────────────────────────────

/** Create a new, empty object (in the first layer with a free index). */
export async function addObject(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage
): Promise<ObjectRef> {
  const objectOrdinal = nextObjectOrdinal(source.seriesInstanceUID);
  return placeObject(servicesManager, commandsManager, source, new Map(), {
    label: `Object ${objectOrdinal}`,
    color: objectColorForOrdinal(objectOrdinal),
    objectOrdinal,
  });
}

/**
 * The object's current voxels, restricted to its populated slices. Scans every slice: brush
 * edits do not maintain the dirty-slice record.
 */
function readObjectSlices(ctx: LabelmapContext, object: ObjectRef): SliceMasks {
  const mask: SliceMasks = new Map();
  ctx.slices.forEach((slice, z) => {
    let sliceMask: Uint8Array | undefined;
    for (let j = 0; j < slice.length; j++) {
      if (slice[j] === object.segmentIndex) {
        sliceMask ??= new Uint8Array(ctx.sliceLen);
        sliceMask[j] = 1;
      }
    }
    if (sliceMask) {
      mask.set(z, sliceMask);
    }
  });
  return mask;
}

/**
 * Visit every row of a prediction crop that lands inside the volume: its viewer slice `z`, the
 * row's start in `crop.seg` and in the labelmap slice. Crop coordinates are model order
 * [z, y, x]; `flipped` reverses z to viewer order. Stops when `visit` returns true.
 */
function forEachCropRow(
  ctx: LabelmapContext,
  crop: PredictionCrop,
  visit: (z: number, srcRow: number, dstRow: number) => boolean | void
): void {
  const nz = ctx.slices.length;
  const [cropZ, cropY, cropX] = crop.cropShape;
  const [z0, y0, x0] = crop.offset;
  for (let i = 0; i < cropZ; i++) {
    const z = crop.flipped ? nz - 1 - (z0 + i) : z0 + i;
    if (z < 0 || z >= nz) {
      continue;
    }
    for (let cy = 0; cy < cropY; cy++) {
      if (visit(z, (i * cropY + cy) * cropX, (y0 + cy) * ctx.columns + x0)) {
        return;
      }
    }
  }
}

/**
 * Write a prediction crop into an object's labelmap. If the new mask would overwrite another
 * object of the same layer, the object is moved to a layer where it fits instead; the result
 * reports where it lives afterwards.
 */
export async function applyCrop(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage,
  target: ObjectRef,
  crop: PredictionCrop
): Promise<ApplyCropResult> {
  const { segmentationId, segmentIndex } = target;
  const ctx = requireLabelmapContext(segmentationId);
  if (crop.fullShape[2] !== ctx.columns || crop.fullShape[1] !== ctx.rows) {
    failHard(
      `prediction shape ${crop.fullShape.join('x')} does not match labelmap ${ctx.rows}x${ctx.columns} for ${segmentationId}`
    );
  }
  const cropX = crop.cropShape[2];

  // Would the prediction take voxels of another object of this layer?
  let overlaps = false;
  forEachCropRow(ctx, crop, (z, srcRow, dstRow) => {
    const slice = ctx.slices[z];
    for (let cx = 0; cx < cropX; cx++) {
      const value = slice[dstRow + cx];
      if (crop.seg[srcRow + cx] && value !== 0 && value !== segmentIndex) {
        return (overlaps = true);
      }
    }
  });
  if (overlaps) {
    return moveObjectWithCrop(servicesManager, commandsManager, source, target, ctx, crop);
  }

  const changed = new Set<number>();
  const written = new Set<number>();
  const previousDirty = getSegmentDirtySlices(segmentationId, segmentIndex);

  if (crop.scope === 'full') {
    for (const z of candidateSlices(ctx, target)) {
      if (clearValueFromSlice(ctx.slices[z], segmentIndex)) {
        changed.add(z);
      }
    }
  }

  forEachCropRow(ctx, crop, (z, srcRow, dstRow) => {
    const slice = ctx.slices[z];
    let rowChanged = false;
    let rowWritten = false;
    for (let cx = 0; cx < cropX; cx++) {
      const j = dstRow + cx;
      if (crop.seg[srcRow + cx]) {
        rowWritten = true;
        if (slice[j] !== segmentIndex) {
          slice[j] = segmentIndex;
          rowChanged = true;
        }
      } else if (crop.scope === 'delta' && slice[j] === segmentIndex) {
        slice[j] = 0;
        rowChanged = true;
      }
    }
    if (rowChanged) {
      changed.add(z);
    }
    if (rowWritten) {
      written.add(z);
    }
  });

  if (crop.scope !== 'delta') {
    updateSegmentDirtyStats(segmentationId, segmentIndex, Array.from(written));
  } else if (previousDirty.known) {
    updateSegmentDirtyStats(segmentationId, segmentIndex, [...previousDirty.slices, ...changed]);
  }
  dispatchModified(segmentationId);

  return { object: target, moved: false, wroteVoxels: written.size > 0 };
}

/** Apply a crop to the object's mask off-labelmap, then re-place the result in another layer. */
async function moveObjectWithCrop(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage,
  from: ObjectRef,
  ctx: LabelmapContext,
  crop: PredictionCrop
): Promise<ApplyCropResult> {
  const cropX = crop.cropShape[2];

  // 'full' replaces the whole mask; 'delta' rewrites only the crop box of the current mask.
  const mask: SliceMasks = crop.scope === 'full' ? new Map() : readObjectSlices(ctx, from);
  forEachCropRow(ctx, crop, (z, srcRow, dstRow) => {
    let sliceMask = mask.get(z);
    for (let cx = 0; cx < cropX; cx++) {
      if (crop.seg[srcRow + cx]) {
        if (!sliceMask) {
          sliceMask = new Uint8Array(ctx.sliceLen);
          mask.set(z, sliceMask);
        }
        sliceMask[dstRow + cx] = 1;
      } else if (sliceMask) {
        sliceMask[dstRow + cx] = 0;
      }
    }
  });
  for (const [z, sliceMask] of mask) {
    if (!sliceMask.some(Boolean)) {
      mask.delete(z);
    }
  }

  // Clear every slice: the index is freed and may be reused by another object.
  for (const slice of ctx.slices) {
    clearValueFromSlice(slice, from.segmentIndex);
  }

  const object = await placeObject(
    servicesManager,
    commandsManager,
    source,
    mask,
    objectMeta(from),
    from.segmentationId
  );
  removeSegmentEntry(from);
  console.info(
    `[nninteractive] object moved ${from.segmentationId}#${from.segmentIndex} → ` +
      `${object.segmentationId}#${object.segmentIndex} (overlaps another object of its layer)`
  );

  return { object, moved: true, wroteVoxels: mask.size > 0 };
}

/**
 * The object's voxel centroid (image and world coordinates), for jumping to it. OHIF's own
 * segment statistics (`cachedStats.center`) are disabled in this mode: recomputing them
 * rewrites a layer's whole segment map and races with object creation.
 */
export function objectCenter(
  object: ObjectRef
): { image: [number, number, number]; world: [number, number, number] } | undefined {
  const ctx = getLabelmapContext(object.segmentationId);
  if (!ctx) {
    return undefined;
  }
  let count = 0;
  let sumX = 0;
  let sumY = 0;
  let sumZ = 0;
  ctx.slices.forEach((slice, z) => {
    for (let j = 0; j < ctx.sliceLen; j++) {
      if (slice[j] === object.segmentIndex) {
        count++;
        sumX += j % ctx.columns;
        sumY += Math.floor(j / ctx.columns);
        sumZ += z;
      }
    }
  });
  if (!count) {
    return undefined;
  }
  const image: [number, number, number] = [sumX / count, sumY / count, sumZ / count];
  const imageId = ctx.sourceImageIds[Math.round(image[2])];
  // imageToWorldCoords takes pixel-edge coordinates: +0.5 addresses the voxel centre.
  const world = csUtils.imageToWorldCoords(imageId, [image[0] + 0.5, image[1] + 0.5]) as number[];
  return { image, world: [world[0], world[1], world[2]] };
}

/**
 * Read one object's full-volume binary mask in viewer slice order (uint8, one byte per
 * voxel). The proxy reshapes to [z, y, x] and reverses z when the series is flipped, so
 * viewer/display-set order is what to send for set_mask.
 */
export function readObjectMask(source: SourceImage, object: ObjectRef): Uint8Array | null {
  const { segmentationId, segmentIndex } = object;
  const ctx = requireLabelmapContext(segmentationId);
  if (source.imageIds.length !== ctx.sourceImageIds.length) {
    failHard(
      `readObjectMask source image count does not match labelmap for ${segmentationId}#${segmentIndex}`
    );
  }
  const mask = new Uint8Array(ctx.sourceImageIds.length * ctx.sliceLen);
  let voxelCount = 0;
  ctx.slices.forEach((slice, z) => {
    const base = z * ctx.sliceLen;
    for (let j = 0; j < ctx.sliceLen; j++) {
      if (slice[j] === segmentIndex) {
        mask[base + j] = 1;
        voxelCount++;
      }
    }
  });
  return voxelCount > 0 ? mask : null;
}

/**
 * Zero all voxels belonging to an object segment (reset). Scans every slice — brush edits do
 * not maintain the dirty-slice record, and a removed object's index may be reused.
 */
export function clearObject({ segmentationId, segmentIndex }: ObjectRef): void {
  const ctx = requireLabelmapContext(segmentationId);
  for (const slice of ctx.slices) {
    clearValueFromSlice(slice, segmentIndex);
  }
  updateSegmentDirtyStats(segmentationId, segmentIndex, []);
  dispatchModified(segmentationId);
}

/**
 * Remove an object entirely: clear its voxels and drop its segment. A layer left without
 * objects is deleted, which frees its labelmap memory.
 */
export async function removeObject(commandsManager: any, object: ObjectRef): Promise<void> {
  const { segmentationId } = object;
  clearObject(object);
  removeSegmentEntry(object);
  if (isManaged(segmentationId) && !segmentIndicesOf(segmentationId).length) {
    await deleteLayer(commandsManager, segmentationId);
  }
}

// ── Import-split ────────────────────────────────────────────────────────────────────────────
// OHIF hydrates a saved DICOM SEG as ONE segmentation with N segments (overlapping SEG →
// several labelmap images per source slice, each holding value = its segment index;
// non-overlapping → one image per slice with values 1..N). Each segment becomes an object,
// packed into layers like any other object, so a non-overlapping SEG loads into one layer.

export type ImportSplitResult = { status: 'skip' | 'done' } | { status: 'retry'; reason: string };

function stripRepresentationsEverywhere(servicesManager: any, segmentationId: string): void {
  const viewportIds =
    servicesManager?.services?.cornerstoneViewportService?.getViewportIds?.() ?? [];
  removeRepresentations(servicesManager, segmentationId, viewportIds);
}

/**
 * Split a freshly-hydrated multi-segment OHIF segmentation into managed objects, preserving
 * each segment's label + color, then hide the original (strip its representations, keep its
 * state). No-op for segmentations this module manages. Returns a status so the caller can
 * retry while hydration data is still settling.
 */
export async function importSplitSegmentation(
  servicesManager: any,
  commandsManager: any,
  hydratedSegmentationId: string,
  source: SourceImage | null
): Promise<ImportSplitResult> {
  if (
    !hydratedSegmentationId ||
    isManaged(hydratedSegmentationId) ||
    splitInProgress.has(hydratedSegmentationId)
  ) {
    return { status: 'skip' };
  }
  if (splitConsumedIds.has(hydratedSegmentationId)) {
    // Already split before — a re-add of its reps just gets re-stripped (never split twice).
    stripRepresentationsEverywhere(servicesManager, hydratedSegmentationId);
    return { status: 'skip' };
  }

  const seg: any = csToolsSegmentation.state.getSegmentation(hydratedSegmentationId);
  const lm: any = seg?.representationData?.[LABELMAP];
  // Every labelmap layer's images: the legacy loader keeps all SEG frames in one layer, the
  // overlap-aware loader spreads them over several layers.
  const layers: any[] = Object.values(lm?.labelmaps ?? {});
  const ids: string[] = Array.from(
    new Set<string>([...(lm?.imageIds ?? []), ...layers.flatMap(layer => layer?.imageIds ?? [])])
  );
  if (!ids.length) {
    return { status: 'skip' }; // volume-only / not a readable stack labelmap
  }
  const segIndices = segmentIndicesOf(hydratedSegmentationId);
  if (!segIndices.length) {
    return { status: 'skip' };
  }
  if (!source?.imageIds?.length) {
    return { status: 'retry', reason: 'active source not resolved yet' };
  }
  const refIds: string[] =
    Array.isArray(lm.referencedImageIds) && lm.referencedImageIds.length
      ? lm.referencedImageIds
      : source.imageIds;
  // Only split a SEG that references the active source series.
  if (refIds.length !== source.imageIds.length) {
    return { status: 'skip' };
  }
  if (ids.some(id => !cache.getImage(id))) {
    return { status: 'retry', reason: 'labelmap images not cached yet' };
  }
  if (!servicesManager?.services?.cornerstoneViewportService?.getViewportIds?.().length) {
    return { status: 'retry', reason: 'no viewports ready' };
  }

  // A layer may store a segment under a label value other than its segment index.
  const segmentIndexByImageAndValue = (imageId: string, value: number): number => {
    for (const layer of layers) {
      if (layer?.imageIds?.includes(imageId)) {
        return Number(layer.labelToSegmentIndex?.[value] ?? value);
      }
    }
    return value;
  };

  splitInProgress.add(hydratedSegmentationId);
  try {
    const firstImg: any = cache.getImage(ids[0]);
    const sliceLen: number =
      firstImg?.voxelManager?.getScalarData?.()?.length ??
      (firstImg?.rows ?? 0) * (firstImg?.columns ?? 0);
    if (!sliceLen) {
      return { status: 'retry', reason: 'labelmap slice geometry not ready' };
    }

    // Layout-agnostic value routing: never index by image position — make ONE pass over ALL
    // labelmap images, route each voxel by its VALUE to that segment's mask at the slice its
    // referencedImageId maps to. Several images can target the same slice (OR-merge).
    // Index by source.imageIds order (what the layers are indexed by), NOT the SEG's
    // referencedImageIds order — same set, but the order is not guaranteed to match.
    const zByRefId = new Map<string, number>();
    source.imageIds.forEach((rid, z) => zByRefId.set(rid, z));
    const masks = new Map<number, SliceMasks>();
    for (const k of segIndices) {
      masks.set(k, new Map());
    }
    let totalCopied = 0;
    for (const id of ids) {
      const img: any = cache.getImage(id);
      const sd = img?.voxelManager?.getScalarData?.();
      const z = zByRefId.get(img?.referencedImageId);
      if (!sd || z === undefined) {
        continue;
      }
      const n = Math.min(sd.length, sliceLen);
      for (let j = 0; j < n; j++) {
        const v = sd[j];
        if (v > 0) {
          const mask = masks.get(segmentIndexByImageAndValue(id, v));
          if (mask) {
            let sliceMask = mask.get(z);
            if (!sliceMask) {
              sliceMask = new Uint8Array(sliceLen);
              mask.set(z, sliceMask);
            }
            sliceMask[j] = 1;
            totalCopied++;
          }
        }
      }
    }
    // Zero voxels means hydration hasn't written the pixel data yet — retry, leave original intact.
    if (totalCopied === 0) {
      return { status: 'retry', reason: 'hydration pixel data not written yet' };
    }

    const created: ObjectRef[] = [];
    for (const k of segIndices) {
      const srcSegment: any = seg.segments[k];
      const objectOrdinal = nextObjectOrdinal(source.seriesInstanceUID);
      const color =
        (Array.isArray(srcSegment?.color) && srcSegment.color) ||
        (Array.isArray(srcSegment?.cachedStats?.color) && srcSegment.cachedStats.color) ||
        objectColorForOrdinal(objectOrdinal);
      created.push(
        await placeObject(servicesManager, commandsManager, source, masks.get(k) as SliceMasks, {
          label: srcSegment?.label || `Object ${objectOrdinal}`,
          color,
          objectOrdinal,
        })
      );
    }

    // Hide the original: strip reps everywhere, keep state, remember it so a re-add is re-stripped.
    splitConsumedIds.add(hydratedSegmentationId);
    stripRepresentationsEverywhere(servicesManager, hydratedSegmentationId);

    // Make the first object active so the next prompt refines it (the hidden original may have been
    // the active segmentation).
    if (created.length) {
      try {
        await commandsManager.run('setActiveSegmentation', {
          segmentationId: created[0].segmentationId,
        });
        csToolsSegmentation.segmentIndex.setActiveSegmentIndex(
          created[0].segmentationId,
          created[0].segmentIndex
        );
      } catch {
        // ignore
      }
    }
    const layerCount = new Set(created.map(object => object.segmentationId)).size;
    console.info(
      `[nninteractive] import-split: ${hydratedSegmentationId} → ${created.length} objects in ` +
        `${layerCount} layer(s) (${totalCopied} voxels)`
    );
    return { status: 'done' };
  } finally {
    splitInProgress.delete(hydratedSegmentationId);
  }
}
