// segmentationBridge: the only module that reads or writes native OHIF/Cornerstone
// segmentation labelmap data.
//
// Data model: ONE OHIF segmentation per nnInteractive object. Each managed
// segmentation has exactly one segment, segmentIndex=1, so objects can overlap
// without competing for values in a shared labelmap.
//
// Storage: the segmentation's stack labelmap images (one derived image per source
// image) are the only voxel store. Cornerstone 5 renders the same images in stack
// viewports and, through an image-backed geometry volume, in MPR viewports — so a
// write here (or a brush stroke in either view) is visible everywhere after
// triggerSegmentationDataModified, with no stack/volume mirroring.

import {
  cache,
  utilities as csUtils,
  BaseVolumeViewport,
  VolumeViewport3D,
} from '@cornerstonejs/core';
import {
  Enums as csToolsEnums,
  segmentation as csToolsSegmentation,
} from '@cornerstonejs/tools';

import { PredictionCrop, SourceImage } from './types';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;

// nnInteractive object segmentations grouped by source series.
const managedSegIdsBySeries = new Map<string, Set<string>>();
// Segmentations this module created (so import logic never re-processes them).
const managedSegIds = new Set<string>();
// Externally-hydrated segmentations already split into per-object segmentations. Their state is
// KEPT (deleting it crashes OHIF's presentation store / toolbar evaluators); a later rep re-add
// (viewport remount, re-hydration of the same SEG) is just re-stripped, never re-split.
const splitConsumedIds = new Set<string>();
// Reentrancy guard while a split runs for one hydrated segmentation.
const splitInProgress = new Set<string>();

export interface ApplyCropResult {
  changedSlices: number[];
  wroteVoxels: boolean;
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
    registerManagedSegmentation(segmentationId, getSeriesInstanceUIDForSegmentation(segmentationId));
    return true;
  }
  return false;
}

export function getSegmentationIdForSeries(seriesInstanceUID: string): string | undefined {
  return getManagedSegmentationIdsForSeries(seriesInstanceUID)[0];
}

function isTaggedManagedSegmentation(seg: any): boolean {
  return seg?.cachedStats?.nninteractiveManaged === true;
}

function registerManagedSegmentation(
  segmentationId: string,
  seriesInstanceUID?: string
): void {
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

export function unregisterManagedSegmentation(segmentationId: string): void {
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

function getObjectOrdinal(segmentationId: string): number {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const ordinal = Number(seg?.cachedStats?.objectOrdinal);
  return Number.isInteger(ordinal) && ordinal > 0 ? ordinal : Number.MAX_SAFE_INTEGER;
}

export function getManagedSegmentationIdsForSeries(seriesInstanceUID: string): string[] {
  const ids = new Set<string>(managedSegIdsBySeries.get(seriesInstanceUID) ?? []);

  // Recover after a state reset by scanning for managed segmentations tagged with the series.
  const all = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];
  for (const seg of all) {
    if (isTaggedManagedSegmentation(seg) && seg?.cachedStats?.seriesInstanceUid === seriesInstanceUID) {
      registerManagedSegmentation(seg.segmentationId, seriesInstanceUID);
      ids.add(seg.segmentationId);
    }
  }

  return Array.from(ids)
    .filter(segmentationId => !!csToolsSegmentation.state.getSegmentation(segmentationId))
    .sort((a, b) => getObjectOrdinal(a) - getObjectOrdinal(b) || a.localeCompare(b));
}

export function getManagedSegmentationIds(): string[] {
  const all = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];
  for (const seg of all) {
    if (isTaggedManagedSegmentation(seg)) {
      registerManagedSegmentation(seg.segmentationId, seg?.cachedStats?.seriesInstanceUid);
    }
  }
  return Array.from(managedSegIds)
    .filter(segmentationId => !!csToolsSegmentation.state.getSegmentation(segmentationId))
    .sort((a, b) => getObjectOrdinal(a) - getObjectOrdinal(b) || a.localeCompare(b));
}

function nextObjectOrdinal(seriesInstanceUID: string): number {
  const ordinals = getManagedSegmentationIdsForSeries(seriesInstanceUID)
    .map(segmentationId => getObjectOrdinal(segmentationId))
    .filter(ordinal => Number.isInteger(ordinal) && ordinal > 0 && ordinal < Number.MAX_SAFE_INTEGER);
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
 * One object's voxel store, indexed by display slice: `slices[z]` is the scalar array of the
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
    const image: any = cache.getImage(labelmapImageIdByReference.get(sourceImageId));
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

function clearValueFromSlice(slice: LabelmapContext['slices'][number], segmentIndex: number): boolean {
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
  return seg?.segments?.[segmentIndex] ?? seg?.segments?.[String(segmentIndex)];
}

function getSegmentDirtySlices(segmentationId: string, segmentIndex: number): {
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
  const segment = {
    ...(segments[segmentIndex] ?? segments[String(segmentIndex)] ?? { segmentIndex }),
  } as any;
  segment.cachedStats = {
    ...(segment.cachedStats ?? {}),
    dirtySlices: unique,
    segZ0: unique.length ? unique[0] : undefined,
    segZ1: unique.length ? unique[unique.length - 1] + 1 : undefined,
  };
  segments[segmentIndex] = segment;
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
    const reps = service.getSegmentationRepresentations(viewportId, {
      segmentationId,
      type: LABELMAP,
    }) ?? [];
    return !reps.some((rep: any) => rep?.segmentationId === segmentationId && rep?.type === LABELMAP);
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
// would keep Cornerstone's default segment-index-1 color (red) there — both the render and
// the panel (which reads the active viewport's representation color) then show all-red.
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

function removeRepresentations(servicesManager: any, segmentationId: string, viewportIds: string[]): void {
  const service = servicesManager.services.segmentationService;
  for (const viewportId of viewportIds) {
    try {
      service.removeRepresentationsFromViewport(viewportId, { segmentationId });
    } catch {
      // ignore — representation may already be gone
    }
  }
}

async function attachRepresentations(servicesManager: any, segmentationId: string): Promise<boolean> {
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
 * Viewport guard: after a layout or viewport change, make every managed segmentation visible
 * (with its object color) in each stack/MPR viewport and absent from 3D viewports.
 */
export async function ensureViewportRepresentations(servicesManager: any): Promise<void> {
  for (const segmentationId of getManagedSegmentationIds()) {
    if (await attachRepresentations(servicesManager, segmentationId)) {
      dispatchModified(segmentationId);
    }
  }
}

// ── Objects ─────────────────────────────────────────────────────────────────────────────────

async function createObjectSegmentation(
  commandsManager: any,
  source: SourceImage,
  objectOrdinal: number
): Promise<string> {
  const segmentationId = csUtils.uuidv4();
  try {
    await commandsManager.run('loadSegmentationsForViewport', {
      segmentations: [
        {
          segmentationId,
          representation: { type: LABELMAP },
          config: { label: `Object ${objectOrdinal}`, segments: {} },
        },
      ],
    });
  } catch (error) {
    failHard('loadSegmentationsForViewport failed', error);
  }
  const created: any = csToolsSegmentation.state.getSegmentation(segmentationId);
  if (!created?.representationData?.[LABELMAP]?.imageIds?.length) {
    failHard(`OHIF did not create a labelmap for segmentation ${segmentationId}`);
  }
  registerManagedSegmentation(segmentationId, source.seriesInstanceUID);
  return segmentationId;
}

/**
 * Create a new one-segment OHIF segmentation for one nnInteractive object.
 */
export async function addObject(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage
): Promise<{ segmentationId: string; segmentIndex: number; created: boolean }> {
  const objectOrdinal = nextObjectOrdinal(source.seriesInstanceUID);
  const segmentationId = await createObjectSegmentation(commandsManager, source, objectOrdinal);

  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const segmentIndex = 1;
  const color = objectColorForOrdinal(objectOrdinal);
  const label = `Object ${objectOrdinal}`;

  csToolsSegmentation.updateSegmentations([
    {
      segmentationId,
      payload: {
        label,
        cachedStats: {
          ...(seg?.cachedStats ?? {}),
          nninteractiveManaged: true,
          seriesInstanceUid: source.seriesInstanceUID,
          displaySetInstanceUID: source.displaySetInstanceUID,
          objectOrdinal,
        },
        segments: {
          [segmentIndex]: {
            segmentIndex,
            color,
            label,
            locked: false,
            active: true,
            cachedStats: { color, dirtySlices: [], objectOrdinal },
          } as any,
        },
      },
    },
  ]);

  await attachRepresentations(servicesManager, segmentationId);

  return { segmentationId, segmentIndex, created: true };
}

/**
 * Write a prediction crop into one object's labelmap.
 * Coordinates in the crop are model order [z, y, x]; `flipped` reverses z to viewer order.
 * Returns the display-set slice indices that changed.
 */
export async function applyCrop(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number,
  crop: PredictionCrop
): Promise<ApplyCropResult> {
  const ctx = requireLabelmapContext(segmentationId);
  const nz = ctx.sourceImageIds.length;
  const nx = ctx.columns;
  if (crop.fullShape[2] !== ctx.columns || crop.fullShape[1] !== ctx.rows) {
    failHard(
      `prediction shape ${crop.fullShape.join('x')} does not match labelmap ${ctx.rows}x${ctx.columns} for ${segmentationId}`
    );
  }

  const changed = new Set<number>();
  const written = new Set<number>();
  const previousDirty = getSegmentDirtySlices(segmentationId, segmentIndex);

  if (crop.scope === 'full') {
    const toClear = previousDirty.known ? previousDirty.slices : ctx.slices.map((_, z) => z);
    for (const z of toClear) {
      if (z < nz && clearValueFromSlice(ctx.slices[z], segmentIndex)) {
        changed.add(z);
      }
    }
  }

  const [cropZ, cropY, cropX] = crop.cropShape;
  const [z0, y0, x0] = crop.offset;
  for (let i = z0; i < z0 + cropZ; i++) {
    const z = crop.flipped ? nz - 1 - i : i;
    if (z < 0 || z >= nz) {
      continue;
    }
    const slice = ctx.slices[z];
    const cropSliceBase = (i - z0) * cropY * cropX;
    let wrote = false;
    for (let cy = 0; cy < cropY; cy++) {
      const srcRow = cropSliceBase + cy * cropX;
      const dstRow = (y0 + cy) * nx + x0;
      for (let cx = 0; cx < cropX; cx++) {
        const dst = dstRow + cx;
        if (crop.seg[srcRow + cx]) {
          if (slice[dst] !== segmentIndex) {
            slice[dst] = segmentIndex;
            wrote = true;
          }
          written.add(z);
        } else if (crop.scope === 'delta' && slice[dst] === segmentIndex) {
          slice[dst] = 0;
          wrote = true;
        }
      }
    }
    if (wrote) {
      changed.add(z);
    }
  }

  const changedSlices = Array.from(changed).sort((a, b) => a - b);
  const writtenSlices = Array.from(written).sort((a, b) => a - b);
  const nextDirty =
    crop.scope === 'delta'
      ? Array.from(new Set([...previousDirty.slices, ...changedSlices])).sort((a, b) => a - b)
      : writtenSlices;
  if (crop.scope !== 'delta' || previousDirty.known) {
    updateSegmentDirtyStats(segmentationId, segmentIndex, nextDirty);
  }
  dispatchModified(segmentationId);

  return { changedSlices, wroteVoxels: writtenSlices.length > 0 };
}

/**
 * Read one object's full-volume binary mask in viewer slice order (uint8, one byte per
 * voxel). The proxy reshapes to [z, y, x] and reverses z when the series is flipped, so
 * viewer/display-set order is what to send for set_mask.
 */
export function readObjectMask(
  servicesManager: any,
  source: SourceImage,
  segmentationId: string,
  segmentIndex: number
): Uint8Array | null {
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

/** Zero all voxels belonging to an object segment (reset). */
export async function clearSegment(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number
): Promise<void> {
  const ctx = requireLabelmapContext(segmentationId);
  const previousDirty = getSegmentDirtySlices(segmentationId, segmentIndex);
  const toClear = previousDirty.known ? previousDirty.slices : ctx.slices.map((_, z) => z);
  for (const z of toClear) {
    if (z < ctx.slices.length) {
      clearValueFromSlice(ctx.slices[z], segmentIndex);
    }
  }
  updateSegmentDirtyStats(segmentationId, segmentIndex, []);
  dispatchModified(segmentationId);
}

/** Remove an object segment entirely (clear voxels + drop the segment entry). */
export async function removeSegment(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number
): Promise<void> {
  await clearSegment(servicesManager, segmentationId, segmentIndex);
  if (isManaged(segmentationId)) {
    return;
  }
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const segments = { ...(seg?.segments ?? {}) };
  delete segments[segmentIndex];
  csToolsSegmentation.updateSegmentations([{ segmentationId, payload: { segments } }]);
  dispatchModified(segmentationId);
}

// ── Import-split ────────────────────────────────────────────────────────────────────────────
// OHIF hydrates a saved DICOM SEG as ONE segmentation with N segments (overlapping SEG → several
// labelmap images per source slice, each holding value = its segment index; non-overlapping → one
// image per slice with values 1..N). The per-object model wants each object as its OWN
// single-segment segmentation, so a loaded SEG is split back into N managed objects, each built
// via addObject (which owns creation + representations).

export type ImportSplitResult =
  | { status: 'skip' }
  | { status: 'consumed' }
  | { status: 'retry'; reason: string }
  | { status: 'done'; created: string[] };

function stripRepresentationsEverywhere(servicesManager: any, segmentationId: string): void {
  const viewportIds = servicesManager?.services?.cornerstoneViewportService?.getViewportIds?.() ?? [];
  removeRepresentations(servicesManager, segmentationId, viewportIds);
}

function applyObjectLabelAndColor(
  servicesManager: any,
  segmentationId: string,
  label: string,
  color: number[]
): void {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const existing: any = seg?.segments?.[1] ?? seg?.segments?.['1'] ?? {};
  const objectOrdinal = seg?.cachedStats?.objectOrdinal;
  csToolsSegmentation.updateSegmentations([
    {
      segmentationId,
      payload: {
        label,
        segments: {
          1: {
            ...existing,
            segmentIndex: 1,
            label,
            color,
            cachedStats: { ...(existing.cachedStats ?? {}), color, objectOrdinal },
          },
        },
      },
    },
  ]);
  applySegmentColors(servicesManager, segmentationId, classifyViewports(servicesManager).planar);
}

// Write a viewer/display-set-order binary mask (1 byte/voxel) into an object's labelmap.
// Returns the display-set slice indices that changed.
function writeFullObjectMask(segmentationId: string, segmentIndex: number, mask: Uint8Array): number[] {
  const ctx = requireLabelmapContext(segmentationId);
  const expected = ctx.sourceImageIds.length * ctx.sliceLen;
  if (mask.length !== expected) {
    failHard(`import-split mask size ${mask.length} does not match labelmap ${expected} for ${segmentationId}`);
  }
  const changed: number[] = [];
  ctx.slices.forEach((slice, z) => {
    const srcBase = z * ctx.sliceLen;
    let wrote = false;
    for (let j = 0; j < ctx.sliceLen; j++) {
      if (mask[srcBase + j]) {
        slice[j] = segmentIndex;
        wrote = true;
      }
    }
    if (wrote) {
      changed.push(z);
    }
  });
  return changed;
}

/**
 * Split a freshly-hydrated multi-segment OHIF segmentation into N managed one-segment objects,
 * preserving each segment's label + color, then hide the original (strip its representations,
 * keep its state). No-op for segmentations this module manages. Returns a status so the caller
 * can retry while hydration data is still settling.
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
    return { status: 'consumed' };
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
  const segIndices = Object.keys(seg?.segments ?? {})
    .map(Number)
    .filter(n => Number.isInteger(n) && n > 0)
    .sort((a, b) => a - b);
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
    // Index by source.imageIds order (what writeFullObjectMask reads back), NOT the SEG's
    // referencedImageIds order — same set, but the order is not guaranteed to match.
    const zByRefId = new Map<string, number>();
    source.imageIds.forEach((rid, z) => zByRefId.set(rid, z));
    const masks = new Map<number, Uint8Array>();
    for (const k of segIndices) {
      masks.set(k, new Uint8Array(source.imageIds.length * sliceLen));
    }
    let totalCopied = 0;
    for (const id of ids) {
      const img: any = cache.getImage(id);
      const sd = img?.voxelManager?.getScalarData?.();
      const z = zByRefId.get(img?.referencedImageId);
      if (!sd || z === undefined) {
        continue;
      }
      const dstBase = z * sliceLen;
      const n = Math.min(sd.length, sliceLen);
      for (let j = 0; j < n; j++) {
        const v = sd[j];
        if (v > 0) {
          const mask = masks.get(segmentIndexByImageAndValue(id, v));
          if (mask) {
            mask[dstBase + j] = 1;
            totalCopied++;
          }
        }
      }
    }
    // Zero voxels means hydration hasn't written the pixel data yet — retry, leave original intact.
    if (totalCopied === 0) {
      return { status: 'retry', reason: 'hydration pixel data not written yet' };
    }

    const created: string[] = [];
    for (const k of segIndices) {
      const srcSegment: any = seg.segments?.[k] ?? seg.segments?.[String(k)];
      const label = srcSegment?.label || `Object ${k}`;
      const color =
        (Array.isArray(srcSegment?.color) && srcSegment.color) ||
        (Array.isArray(srcSegment?.cachedStats?.color) && srcSegment.cachedStats.color) ||
        objectColorForOrdinal(created.length + 1);

      const { segmentationId: newId } = await addObject(servicesManager, commandsManager, source);
      created.push(newId);
      applyObjectLabelAndColor(servicesManager, newId, label, color);

      const changed = writeFullObjectMask(newId, 1, masks.get(k) as Uint8Array);
      updateSegmentDirtyStats(newId, 1, changed);
      dispatchModified(newId);
    }

    // Hide the original: strip reps everywhere, keep state, remember it so a re-add is re-stripped.
    splitConsumedIds.add(hydratedSegmentationId);
    stripRepresentationsEverywhere(servicesManager, hydratedSegmentationId);

    // Make the first object active so the next prompt refines it (the hidden original may have been
    // the active segmentation).
    if (created.length) {
      try {
        await commandsManager.run('setActiveSegmentation', { segmentationId: created[0] });
      } catch {
        // ignore
      }
    }
    console.info(
      `[nninteractive] import-split: ${hydratedSegmentationId} → ${created.length} objects (${totalCopied} voxels)`
    );
    return { status: 'done', created };
  } finally {
    splitInProgress.delete(hydratedSegmentationId);
  }
}
