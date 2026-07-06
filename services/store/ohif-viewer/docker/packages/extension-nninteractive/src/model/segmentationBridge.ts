// segmentationBridge: the only module that reads or writes native OHIF/Cornerstone
// segmentation labelmap data.
//
// Data model (docs/nninteractive-ohif-ideal-architecture.md §11): ONE OHIF
// segmentation per source series, ONE segment per nnInteractive object. Segment value
// N in the shared labelmap is object N. This is native to OHIF, fast with many
// objects, and makes the brush target unambiguous (active segment = active object).
//
// The authoritative voxel store is OHIF's native labelmap volume. Stack labelmap images
// are kept only as OHIF/export compatibility mirrors.

import {
  cache,
  metaData,
  utilities as csUtils,
  BaseVolumeViewport,
  VolumeViewport3D,
  eventTarget,
} from '@cornerstonejs/core';
import {
  Enums as csToolsEnums,
  segmentation as csToolsSegmentation,
} from '@cornerstonejs/tools';
import { convertStackToVolumeLabelmap } from '@cornerstonejs/tools/segmentation/helpers/convertStackToVolumeLabelmap';

import { PredictionCrop, SourceImage } from './types';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;
const STREAMING_VOLUME_PREFIX = 'cornerstoneStreamingImageVolume:';

// One nnInteractive segmentation per source series.
const segIdBySeries = new Map<string, string>();
// Segmentations whose MPR volume has unsynced manual (brush) edits.
const mprDirtySegIds = new Set<string>();
// Segmentations this module created (so import logic never re-processes them).
const managedSegIds = new Set<string>();
// Segmentations whose GPU labelmap texture has been kicked once (first-render workaround).
const textureKicked = new Set<string>();
const pendingMprLogKeys = new Set<string>();
const geometryNormalizedLogKeys = new Set<string>();

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
  return managedSegIds.has(segmentationId);
}

export function getSegmentationIdForSeries(seriesInstanceUID: string): string | undefined {
  const known = segIdBySeries.get(seriesInstanceUID);
  if (known && csToolsSegmentation.state.getSegmentation(known)) {
    return known;
  }
  // Recover after a state reset by scanning for a managed segmentation tagged with the series.
  const all = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];
  const match = all.find(
    seg => managedSegIds.has(seg.segmentationId) && seg?.cachedStats?.seriesInstanceUid === seriesInstanceUID
  );
  if (match) {
    segIdBySeries.set(seriesInstanceUID, match.segmentationId);
    return match.segmentationId;
  }
  return undefined;
}

function dispatchModified(segmentationId: string): void {
  eventTarget.dispatchEvent(
    new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
      detail: { segmentationId },
    })
  );
}

function failHard(message: string, detail?: unknown): never {
  if (detail !== undefined) {
    console.error(`[nninteractive] ${message}`, detail);
  } else {
    console.error(`[nninteractive] ${message}`);
  }
  throw new Error(`[nninteractive] ${message}`);
}

export function getNativeLabelmapVolume(servicesManager: any, segmentationId: string): any | null {
  const service = servicesManager?.services?.segmentationService;
  if (typeof service?.getLabelmapVolume !== 'function') {
    return null;
  }
  try {
    const vol = service.getLabelmapVolume(segmentationId);
    const vm = vol?.voxelManager;
    if (vol && vm?.getCompleteScalarDataArray && vm?.setCompleteScalarDataArray) {
      normalizeNativeLabelmapGeometry(segmentationId, vol);
      return vol;
    }
  } catch (error) {
    failHard(`segmentationService.getLabelmapVolume failed for ${segmentationId}`, error);
  }
  return null;
}

function requireNativeLabelmapVolume(servicesManager: any, segmentationId: string): any {
  const vol = getNativeLabelmapVolume(servicesManager, segmentationId);
  if (!vol) {
    failHard(`native OHIF labelmap volume is required for segmentation ${segmentationId}`);
  }
  return vol;
}

function getNativeLabelmapVolumeId(volume: any): string | undefined {
  if (typeof volume?.volumeId === 'string' && volume.volumeId) {
    return volume.volumeId;
  }
  return undefined;
}

function ensureLabelmapVolumeReference(
  segmentationId: string,
  volume: any
): boolean {
  const volumeId = getNativeLabelmapVolumeId(volume);
  if (!volumeId) {
    return false;
  }
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const repData: any = seg?.representationData || {};
  const lm: any = repData[LABELMAP] || {};
  if (lm.volumeId === volumeId) {
    return true;
  }
  csToolsSegmentation.updateSegmentations([
    {
      segmentationId,
      payload: {
        representationData: { ...repData, [LABELMAP]: { ...lm, volumeId } },
      },
    },
  ]);
  return true;
}

function sourceVolumeIdForDisplaySet(displaySetInstanceUID: string): string {
  return displaySetInstanceUID.startsWith(STREAMING_VOLUME_PREFIX)
    ? displaySetInstanceUID
    : `${STREAMING_VOLUME_PREFIX}${displaySetInstanceUID}`;
}

function coerceFiniteNumbers(values: unknown, expectedLength: number): number[] | null {
  const arrayLike = values as ArrayLike<unknown> | undefined;
  if (
    !arrayLike ||
    typeof arrayLike !== 'object' ||
    typeof arrayLike.length !== 'number' ||
    arrayLike.length < expectedLength
  ) {
    return null;
  }

  const result: number[] = [];
  for (let i = 0; i < expectedLength; i++) {
    const value = Number(arrayLike[i]);
    if (!Number.isFinite(value)) {
      return null;
    }
    result.push(value);
  }
  return result;
}

function isNativeNumberArray(values: unknown, expectedLength: number): boolean {
  const arrayLike = values as ArrayLike<unknown> | undefined;
  if (
    !arrayLike ||
    typeof arrayLike !== 'object' ||
    typeof arrayLike.length !== 'number' ||
    arrayLike.length < expectedLength
  ) {
    return false;
  }
  for (let i = 0; i < expectedLength; i++) {
    if (typeof arrayLike[i] !== 'number' || !Number.isFinite(arrayLike[i] as number)) {
      return false;
    }
  }
  return true;
}

function getReferencedSourceVolume(segmentationId: string): any | null {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const lm: any = seg?.representationData?.[LABELMAP];
  const referencedVolumeId =
    typeof lm?.referencedVolumeId === 'string' && lm.referencedVolumeId
      ? lm.referencedVolumeId
      : typeof seg?.cachedStats?.displaySetInstanceUID === 'string'
        ? seg.cachedStats.displaySetInstanceUID
        : undefined;

  if (!referencedVolumeId) {
    return null;
  }

  try {
    return cache.getVolume(sourceVolumeIdForDisplaySet(referencedVolumeId)) ?? null;
  } catch {
    return null;
  }
}

function setVolumeGeometry(
  volume: any,
  geometry: { spacing: number[]; origin: number[]; direction: number[] }
): void {
  volume.spacing = geometry.spacing;
  volume.origin = geometry.origin;
  volume.direction = geometry.direction;
  volume.imageData?.setSpacing?.(geometry.spacing);
  volume.imageData?.setOrigin?.(geometry.origin);
  volume.imageData?.setDirection?.(geometry.direction);
  volume.imageData?.modified?.();
}

function normalizeNativeLabelmapGeometry(segmentationId: string, labelmapVolume: any): void {
  const sourceVolume = getReferencedSourceVolume(segmentationId);
  const spacing =
    coerceFiniteNumbers(sourceVolume?.spacing, 3) ??
    coerceFiniteNumbers(sourceVolume?.imageData?.getSpacing?.(), 3) ??
    coerceFiniteNumbers(labelmapVolume?.spacing, 3) ??
    coerceFiniteNumbers(labelmapVolume?.imageData?.getSpacing?.(), 3);
  const origin =
    coerceFiniteNumbers(sourceVolume?.origin, 3) ??
    coerceFiniteNumbers(sourceVolume?.imageData?.getOrigin?.(), 3) ??
    coerceFiniteNumbers(labelmapVolume?.origin, 3) ??
    coerceFiniteNumbers(labelmapVolume?.imageData?.getOrigin?.(), 3);
  const direction =
    coerceFiniteNumbers(sourceVolume?.direction, 9) ??
    coerceFiniteNumbers(sourceVolume?.imageData?.getDirection?.(), 9) ??
    coerceFiniteNumbers(labelmapVolume?.direction, 9) ??
    coerceFiniteNumbers(labelmapVolume?.imageData?.getDirection?.(), 9);

  if (!spacing) {
    failHard(`native labelmap volume ${segmentationId} has non-finite spacing`);
  }
  if (!origin) {
    failHard(`native labelmap volume ${segmentationId} has non-finite origin`);
  }
  if (!direction) {
    failHard(`native labelmap volume ${segmentationId} has non-finite direction`);
  }

  const needsNormalization =
    !isNativeNumberArray(labelmapVolume?.spacing, 3) ||
    !isNativeNumberArray(labelmapVolume?.origin, 3) ||
    !isNativeNumberArray(labelmapVolume?.direction, 9) ||
    !isNativeNumberArray(labelmapVolume?.imageData?.getSpacing?.(), 3) ||
    !isNativeNumberArray(labelmapVolume?.imageData?.getOrigin?.(), 3) ||
    !isNativeNumberArray(labelmapVolume?.imageData?.getDirection?.(), 9);

  setVolumeGeometry(labelmapVolume, { spacing, origin, direction });

  const volumeId = getNativeLabelmapVolumeId(labelmapVolume) ?? segmentationId;
  if (needsNormalization && !geometryNormalizedLogKeys.has(volumeId)) {
    geometryNormalizedLogKeys.add(volumeId);
    console.info('[nninteractive] normalized native labelmap volume geometry', {
      segmentationId,
      volumeId,
      spacing,
      origin,
      direction,
    });
  }
}

function preferCanonicalReferencedVolumeId(
  current: string | undefined,
  next: string | undefined
): string | undefined {
  if (!next) {
    return current;
  }
  if (!current || current === next) {
    return next;
  }
  if (!current.startsWith(STREAMING_VOLUME_PREFIX) && next.startsWith(STREAMING_VOLUME_PREFIX)) {
    return next;
  }
  return current;
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

function ensureLabelmapReferenceData(
  segmentationId: string,
  data: { imageIds?: string[]; referencedImageIds?: string[]; referencedVolumeId?: string }
): void {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  if (!seg) {
    return;
  }
  const repData: any = seg.representationData || {};
  const lm: any = repData[LABELMAP] || {};
  const next = {
    ...lm,
    imageIds: lm.imageIds?.length ? lm.imageIds : data.imageIds,
    referencedImageIds: lm.referencedImageIds?.length ? lm.referencedImageIds : data.referencedImageIds,
    referencedVolumeId: preferCanonicalReferencedVolumeId(
      lm.referencedVolumeId,
      data.referencedVolumeId
    ),
  };
  csToolsSegmentation.updateSegmentations([
    {
      segmentationId,
      payload: {
        representationData: { ...repData, [LABELMAP]: next },
      },
    },
  ]);
}

async function ensureNativeLabelmapVolume(
  servicesManager: any,
  segmentationId: string,
  referenceData?: { imageIds?: string[]; referencedImageIds?: string[]; referencedVolumeId?: string }
): Promise<any> {
  const existing = getNativeLabelmapVolume(servicesManager, segmentationId);
  if (existing) {
    if (referenceData) {
      ensureLabelmapReferenceData(segmentationId, referenceData);
    }
    if (!ensureLabelmapVolumeReference(segmentationId, existing)) {
      failHard(`native labelmap volume for ${segmentationId} has no usable volumeId`);
    }
    return existing;
  }

  const segmentation = csToolsSegmentation.state.getSegmentation(segmentationId);
  const labelmap = segmentation?.representationData?.[LABELMAP];
  if (!segmentation || !Array.isArray(labelmap?.imageIds) || !labelmap.imageIds.length) {
    failHard(`cannot materialize native labelmap volume for ${segmentationId}: OHIF labelmap imageIds are missing`);
  }

  try {
    await convertStackToVolumeLabelmap({ segmentationId });
  } catch (error) {
    failHard(`convertStackToVolumeLabelmap failed for ${segmentationId}`, error);
  }

  if (referenceData) {
    ensureLabelmapReferenceData(segmentationId, referenceData);
  }

  const volume = requireNativeLabelmapVolume(servicesManager, segmentationId);
  if (!ensureLabelmapVolumeReference(segmentationId, volume)) {
    failHard(`native labelmap volume for ${segmentationId} has no usable volumeId`);
  }
  return volume;
}

function volumeKForDisplaySlice(
  volume: any,
  sourceImageIds: string[],
  displaySlice: number
): number {
  if (displaySlice < 0 || displaySlice >= sourceImageIds.length) {
    return -1;
  }
  const sourceImageId = sourceImageIds[displaySlice];
  const volumeImageIds: string[] = volume?.imageIds ?? volume?.voxelManager?.getImageIds?.() ?? [];
  const direct = sourceImageId ? volumeImageIds.indexOf(sourceImageId) : -1;
  if (direct >= 0) {
    return direct;
  }
  const plane: any = sourceImageId ? metaData.get('imagePlaneModule', sourceImageId) : null;
  const ipp = plane?.imagePositionPatient;
  if (ipp && volume?.imageData) {
    const k = csUtils.transformWorldToIndex(volume.imageData, ipp)?.[2];
    if (Number.isFinite(k)) {
      return Math.round(k);
    }
  }
  return displaySlice < (volume?.dimensions?.[2] ?? 0) ? displaySlice : -1;
}

function displaySliceForVolumeK(volume: any, sourceImageIds: string[], k: number): number {
  const volumeImageIds: string[] = volume?.imageIds ?? volume?.voxelManager?.getImageIds?.() ?? [];
  const imageId = volumeImageIds[k];
  if (imageId && sourceImageIds.length) {
    const idx = sourceImageIds.indexOf(imageId);
    if (idx >= 0) {
      return idx;
    }
  }
  return k < sourceImageIds.length ? k : -1;
}

function getLabelmapImageIds(segmentationId: string): string[] {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  return seg?.representationData?.[LABELMAP]?.imageIds ?? [];
}

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

function classifyViewports(servicesManager: any): {
  stack: string[];
  mpr: string[];
  pendingMpr: string[];
  volume3d: string[];
} {
  const cvs = servicesManager.services.cornerstoneViewportService;
  const stack: string[] = [];
  const mpr: string[] = [];
  const pendingMpr: string[] = [];
  const volume3d: string[] = [];
  for (const viewportId of cvs.getViewportIds()) {
    const vp = cvs.getCornerstoneViewport(viewportId);
    if (vp instanceof VolumeViewport3D) {
      volume3d.push(viewportId);
    } else if (vp instanceof BaseVolumeViewport) {
      if (isMprViewportVolumeReady(vp)) {
        mpr.push(viewportId);
      } else {
        pendingMpr.push(viewportId);
      }
    } else {
      stack.push(viewportId);
    }
  }
  return { stack, mpr, pendingMpr, volume3d };
}

function isMprViewportVolumeReady(viewport: any): boolean {
  try {
    const volumeId = viewport?.getVolumeId?.();
    if (typeof volumeId !== 'string' || !volumeId) {
      return false;
    }
    return !!cache.getVolume(volumeId);
  } catch {
    return false;
  }
}

function logPendingMprOnce(viewportIds: string[]): void {
  if (!viewportIds.length) {
    pendingMprLogKeys.clear();
    return;
  }
  const key = viewportIds.slice().sort().join(',');
  if (pendingMprLogKeys.has(key)) {
    return;
  }
  pendingMprLogKeys.add(key);
  console.info('[nninteractive] MPR guard waiting for source volume', viewportIds);
}

function setSegmentColor(
  servicesManager: any,
  viewportIds: string[],
  segmentationId: string,
  segmentIndex: number,
  color: number[]
): void {
  const service: any = servicesManager.services.segmentationService;
  if (typeof service.setSegmentColor !== 'function') {
    return;
  }
  for (const viewportId of viewportIds) {
    try {
      service.setSegmentColor(viewportId, segmentationId, segmentIndex, color);
    } catch {
      // ignore — color is a display nicety
    }
  }
}

function getRepresentationsMissing(
  servicesManager: any,
  segmentationId: string,
  viewportIds: string[]
): string[] {
  const service = servicesManager.services.segmentationService;
  return viewportIds.filter(viewportId => {
    try {
      const reps = service.getSegmentationRepresentations?.(viewportId, {
        segmentationId,
        type: LABELMAP,
      }) ?? [];
      return !reps.some((rep: any) => rep?.segmentationId === segmentationId && rep?.type === LABELMAP);
    } catch (error) {
      failHard(`could not inspect segmentation representations for ${segmentationId} in ${viewportId}`, error);
    }
  });
}

function setSegmentColorsForViewports(
  servicesManager: any,
  segmentationId: string,
  viewportIds: string[]
): void {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const segments = Object.values(seg?.segments ?? {}) as any[];
  for (const segment of segments) {
    const segmentIndex = Number(segment?.segmentIndex);
    const color = segment?.cachedStats?.color ?? segment?.color;
    if (Number.isInteger(segmentIndex) && Array.isArray(color)) {
      setSegmentColor(servicesManager, viewportIds, segmentationId, segmentIndex, color);
    }
  }
}

async function ensureMprRepresentations(
  servicesManager: any,
  segmentationId: string,
  mprViewportIds: string[]
): Promise<void> {
  const service = servicesManager.services.segmentationService;
  const missing = getRepresentationsMissing(servicesManager, segmentationId, mprViewportIds);
  for (const viewportId of missing) {
    try {
      await service.addSegmentationRepresentation(viewportId, { segmentationId });
    } catch (error) {
      failHard(`could not add MPR representation for ${segmentationId} in ${viewportId}`, error);
    }
  }
  if (missing.length) {
    setSegmentColorsForViewports(servicesManager, segmentationId, missing);
  }
}

function ensureNativeVolumeReferenceForMpr(servicesManager: any, segmentationId: string): void {
  ensureSourceVolumeReferenceForMpr(segmentationId);
  const nativeVolume = requireNativeLabelmapVolume(servicesManager, segmentationId);
  if (!ensureLabelmapVolumeReference(segmentationId, nativeVolume)) {
    failHard(`native labelmap volume for ${segmentationId} has no usable volumeId`);
  }
}

function ensureSourceVolumeReferenceForMpr(segmentationId: string): void {
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const lm: any = seg?.representationData?.[LABELMAP];
  const referencedVolumeId = lm?.referencedVolumeId;
  if (typeof referencedVolumeId !== 'string' || !referencedVolumeId) {
    failHard(`segmentation ${segmentationId} has no referenced source volume id for MPR`);
  }
  const sourceVolumeId = sourceVolumeIdForDisplaySet(referencedVolumeId);
  if (!cache.getVolume(sourceVolumeId)) {
    failHard(`referenced source volume ${sourceVolumeId} is not cached for MPR segmentation ${segmentationId}`);
  }
  if (referencedVolumeId !== sourceVolumeId) {
    ensureLabelmapReferenceData(segmentationId, { referencedVolumeId: sourceVolumeId });
  }
}

async function mprReadyForGlobalDispatch(
  servicesManager: any,
  segmentationId: string
): Promise<boolean> {
  const { mpr } = classifyViewports(servicesManager);
  if (!mpr.length) {
    return true;
  }
  ensureNativeVolumeReferenceForMpr(servicesManager, segmentationId);
  await ensureMprRepresentations(servicesManager, segmentationId, mpr);
  return true;
}

export function flushAuthoritativeLabelmap(
  servicesManager: any,
  segmentationId: string,
  direction: 'volumeToStack' | 'stackToVolume' = 'volumeToStack',
  changedStackIdxs?: number[]
): boolean {
  let ok: boolean;
  if (direction === 'stackToVolume') {
    ok = copyStackToVolume(
      segmentationId,
      requireNativeLabelmapVolume(servicesManager, segmentationId),
      changedStackIdxs
    );
  } else {
    ok = copyVolumeToStack(servicesManager, segmentationId, changedStackIdxs);
  }
  if (!ok) {
    failHard(`authoritative labelmap ${direction} flush failed for ${segmentationId}`);
  }
  return ok;
}

function copyStackToVolume(
  segmentationId: string,
  labelmapVol: any,
  changedStackIdxs?: number[]
): boolean {
  try {
    const vm = labelmapVol?.voxelManager;
    if (!vm?.getCompleteScalarDataArray || !vm?.setCompleteScalarDataArray) {
      return false;
    }
    const arr = vm.getCompleteScalarDataArray();
    const [nx, ny, nz] = labelmapVol.dimensions;
    const sliceLen = nx * ny;
    const sourceImageIds = getSourceImageIdsForSegmentation(segmentationId);
    if (!sourceImageIds.length) {
      return false;
    }
    const stackImageIds = getLabelmapImageIds(segmentationId);
    const displaySlices = Array.isArray(changedStackIdxs)
      ? changedStackIdxs
      : Array.from({ length: sourceImageIds.length }, (_, i) => i);

    for (const displaySlice of displaySlices) {
      const k = volumeKForDisplaySlice(labelmapVol, sourceImageIds, displaySlice);
      if (k < 0 || k >= nz) {
        continue;
      }
      const segImg: any = cache.getImage(stackImageIds[displaySlice]);
      if (!segImg) {
        continue;
      }
      const sd = segImg.voxelManager?.getScalarData?.();
      if (!sd || sd.length !== sliceLen) {
        continue;
      }
      (arr as any).set?.(sd, k * sliceLen);
      if (!(arr as any).set) {
        for (let j = 0; j < sliceLen; j++) {
          (arr as any)[k * sliceLen + j] = sd[j];
        }
      }
    }
    vm.setCompleteScalarDataArray(arr);
    mprDirtySegIds.delete(segmentationId);
    return true;
  } catch (error) {
    failHard(`stack-to-volume sync failed for ${segmentationId}`, error);
  }
}

function copyVolumeToStack(
  servicesManager: any,
  segmentationId: string,
  changedStackIdxs?: number[]
): boolean {
  try {
    const labelmapVol = getNativeLabelmapVolume(servicesManager, segmentationId);
    const vm = labelmapVol?.voxelManager;
    if (!labelmapVol || !vm?.getCompleteScalarDataArray) {
      return false;
    }
    const arr = vm.getCompleteScalarDataArray();
    const [nx, ny, nz] = labelmapVol.dimensions;
    const sliceLen = nx * ny;
    const sourceImageIds = getSourceImageIdsForSegmentation(segmentationId);
    if (!sourceImageIds.length) {
      return false;
    }
    const stackImageIds = getLabelmapImageIds(segmentationId);
    const displaySlices = Array.isArray(changedStackIdxs)
      ? changedStackIdxs
      : Array.from({ length: sourceImageIds.length }, (_, i) => i);

    for (const displaySlice of displaySlices) {
      const k = volumeKForDisplaySlice(labelmapVol, sourceImageIds, displaySlice);
      if (k < 0 || k >= nz) {
        continue;
      }
      const segImg: any = cache.getImage(stackImageIds[displaySlice]);
      if (!segImg) {
        continue;
      }
      const sd = segImg.voxelManager?.getScalarData?.();
      if (!sd || sd.length !== sliceLen) {
        continue;
      }
      const src = arr.subarray?.(k * sliceLen, (k + 1) * sliceLen);
      if (sd.set && src) {
        sd.set(src);
      } else {
        const base = k * sliceLen;
        for (let j = 0; j < sliceLen; j++) {
          sd[j] = arr[base + j];
        }
      }
      segImg.voxelManager?.setScalarData?.(sd);
    }
    mprDirtySegIds.delete(segmentationId);
    return true;
  } catch (error) {
    failHard(`volume-to-stack sync failed for ${segmentationId}`, error);
  }
}

/** Copy the authoritative labelmap volume back into the stack labelmap. */
export function syncMprToStack(servicesManager: any, segmentationId: string): boolean {
  return flushAuthoritativeLabelmap(servicesManager, segmentationId, 'volumeToStack');
}

async function attachRepresentations(
  servicesManager: any,
  segmentationId: string
): Promise<void> {
  const service = servicesManager.services.segmentationService;
  const { stack, mpr, volume3d } = classifyViewports(servicesManager);

  for (const viewportId of getRepresentationsMissing(servicesManager, segmentationId, stack)) {
    try {
      await service.addSegmentationRepresentation(viewportId, { segmentationId });
    } catch (error) {
      failHard(`could not add stack representation for ${segmentationId} in ${viewportId}`, error);
    }
  }
  // Labelmap→surface in a 3D viewport crashes polySeg — never attach there.
  for (const viewportId of volume3d) {
    try {
      service.removeSegmentationRepresentations(viewportId, { segmentationId });
    } catch {
      // ignore
    }
  }
  if (mpr.length) {
    ensureNativeVolumeReferenceForMpr(servicesManager, segmentationId);
    await ensureMprRepresentations(servicesManager, segmentationId, mpr);
  }
}

async function runLoadSegmentationsForViewport(
  commandsManager: any,
  segmentations: any[]
): Promise<void> {
  if (typeof commandsManager?.run !== 'function') {
    failHard('commandsManager.run is required to load OHIF segmentations');
  }
  try {
    await commandsManager.run('loadSegmentationsForViewport', { segmentations });
  } catch (error) {
    failHard('loadSegmentationsForViewport failed', error);
  }
}

async function ensureNativeSegmentation(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage
): Promise<{ segmentationId: string; created: boolean }> {
  let segmentationId = getSegmentationIdForSeries(source.seriesInstanceUID);
  if (segmentationId) {
    return { segmentationId, created: false };
  }

  segmentationId = csUtils.uuidv4();
  const segmentation = {
    segmentationId,
    representation: {
      type: LABELMAP,
    },
    config: {
      cachedStats: {
        seriesInstanceUid: source.seriesInstanceUID,
        displaySetInstanceUID: source.displaySetInstanceUID,
      },
      label: source.seriesDescription || 'nnInteractive',
      segments: {},
    },
  } as any;

  await runLoadSegmentationsForViewport(commandsManager, [segmentation]);
  const existing = csToolsSegmentation.state.getSegmentation(segmentationId);
  const existingLabelmap: any = existing?.representationData?.[LABELMAP];
  if (!existing) {
    failHard(`OHIF did not create segmentation ${segmentationId}`);
  }
  if (!existingLabelmap?.imageIds?.length) {
    failHard(`OHIF segmentation ${segmentationId} has no labelmap imageIds`);
  }
  const labelmapData = {
    imageIds: existingLabelmap?.imageIds?.length ? existingLabelmap.imageIds : undefined,
    referencedVolumeId: preferCanonicalReferencedVolumeId(
      existingLabelmap?.referencedVolumeId,
      sourceVolumeIdForDisplaySet(source.displaySetInstanceUID)
    ),
    referencedImageIds: existingLabelmap?.referencedImageIds?.length
      ? existingLabelmap.referencedImageIds
      : source.imageIds,
  };
  ensureLabelmapReferenceData(segmentationId, labelmapData);
  await ensureNativeLabelmapVolume(servicesManager, segmentationId, labelmapData);
  managedSegIds.add(segmentationId);
  segIdBySeries.set(source.seriesInstanceUID, segmentationId);
  return { segmentationId, created: true };
}

/**
 * Ensure a segmentation exists for the series and add a new object segment to it.
 * Returns the object's identity and whether the segmentation was just created.
 */
export async function addObject(
  servicesManager: any,
  commandsManager: any,
  source: SourceImage
): Promise<{ segmentationId: string; segmentIndex: number; created: boolean }> {
  const ensured = await ensureNativeSegmentation(servicesManager, commandsManager, source);
  const { segmentationId, created } = ensured;
  await ensureNativeLabelmapVolume(servicesManager, segmentationId);

  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const existing = created ? {} : { ...(seg?.segments ?? {}) };
  const indices = Object.keys(existing).map(Number).filter(n => Number.isInteger(n) && n > 0);
  const segmentIndex = indices.length ? Math.max(...indices) + 1 : 1;
  const color = objectColorForOrdinal(segmentIndex);

  existing[segmentIndex] = {
    segmentIndex,
    color,
    label: `Object ${segmentIndex}`,
    locked: false,
    active: true,
    cachedStats: { color, dirtySlices: [] },
  } as any;

  csToolsSegmentation.updateSegmentations([{ segmentationId, payload: { segments: existing } }]);

  if (created) {
    await attachRepresentations(servicesManager, segmentationId);
  }

  const { stack, mpr } = classifyViewports(servicesManager);
  setSegmentColor(servicesManager, [...stack, ...mpr], segmentationId, segmentIndex, color);

  return { segmentationId, segmentIndex, created };
}

/**
 * Write a prediction crop into the shared stack labelmap for one object segment.
 * Coordinates in the crop are model order [z, y, x]; `flipped` reverses z to viewer order.
 * Returns the display-set slice indices that changed (for incremental MPR sync).
 */
export async function applyCrop(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number,
  crop: PredictionCrop
): Promise<ApplyCropResult> {
  await ensureNativeLabelmapVolume(servicesManager, segmentationId);
  const volumeApplied = applyCropToVolume(servicesManager, segmentationId, segmentIndex, crop);
  if (volumeApplied) {
    flushAuthoritativeLabelmap(
      servicesManager,
      segmentationId,
      'volumeToStack',
      volumeApplied.changedSlices
    );
    if (await mprReadyForGlobalDispatch(servicesManager, segmentationId)) {
      dispatchModified(segmentationId);
    }
    if (!textureKicked.has(segmentationId)) {
      textureKicked.add(segmentationId);
      kickStackTexture(servicesManager);
    }
    return volumeApplied;
  }

  failHard(
    `applyCrop requires a native OHIF labelmap volume matching crop dimensions for ${segmentationId}#${segmentIndex}`
  );
}

function kickStackTexture(servicesManager: any): void {
  try {
    const { cornerstoneViewportService, viewportGridService } = servicesManager.services;
    const viewportId = viewportGridService?.getActiveViewportId?.();
    const vp: any = viewportId ? cornerstoneViewportService?.getCornerstoneViewport?.(viewportId) : null;
    if (!vp || vp instanceof BaseVolumeViewport || typeof vp.setImageIdIndex !== 'function') {
      return;
    }
    const idx = vp.getCurrentImageIdIndex?.() ?? 0;
    const away = idx === 0 ? 1 : 0;
    Promise.resolve(vp.setImageIdIndex(away)).then(() => vp.setImageIdIndex(idx));
  } catch {
    // ignore — a missed kick only delays the first texture upload to the next render
  }
}

function getVolumeContext(servicesManager: any, segmentationId: string): {
  vol: any;
  arr: any;
  nx: number;
  ny: number;
  nz: number;
  sliceLen: number;
  sourceImageIds: string[];
} | null {
  const vol = getNativeLabelmapVolume(servicesManager, segmentationId);
  const vm = vol?.voxelManager;
  if (!vol || !vm?.getCompleteScalarDataArray || !vm?.setCompleteScalarDataArray) {
    return null;
  }
  const sourceImageIds = getSourceImageIdsForSegmentation(segmentationId);
  if (!sourceImageIds.length) {
    return null;
  }
  const [nx, ny, nz] = vol.dimensions ?? [];
  if (!nx || !ny || !nz) {
    return null;
  }
  return {
    vol,
    arr: vm.getCompleteScalarDataArray(),
    nx,
    ny,
    nz,
    sliceLen: nx * ny,
    sourceImageIds,
  };
}

function clearObjectFromVolumeSlice(
  ctx: { arr: any; sliceLen: number },
  k: number,
  segmentIndex: number
): boolean {
  let changed = false;
  const base = k * ctx.sliceLen;
  for (let j = 0; j < ctx.sliceLen; j++) {
    if (ctx.arr[base + j] === segmentIndex) {
      ctx.arr[base + j] = 0;
      changed = true;
    }
  }
  return changed;
}

function applyCropToVolume(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number,
  crop: PredictionCrop
): ApplyCropResult | null {
  const ctx = getVolumeContext(servicesManager, segmentationId);
  if (!ctx || ctx.nx !== crop.fullShape[2] || ctx.ny !== crop.fullShape[1]) {
    return null;
  }

  const changed = new Set<number>();
  const written = new Set<number>();
  const previousDirty = getSegmentDirtySlices(segmentationId, segmentIndex);

  if (crop.scope === 'full') {
    if (previousDirty.known) {
      for (const displaySlice of previousDirty.slices) {
        const k = volumeKForDisplaySlice(ctx.vol, ctx.sourceImageIds, displaySlice);
        if (k >= 0 && k < ctx.nz && clearObjectFromVolumeSlice(ctx, k, segmentIndex)) {
          changed.add(displaySlice);
        }
      }
    } else {
      for (let k = 0; k < ctx.nz; k++) {
        if (clearObjectFromVolumeSlice(ctx, k, segmentIndex)) {
          const displaySlice = displaySliceForVolumeK(ctx.vol, ctx.sourceImageIds, k);
          if (displaySlice >= 0) {
            changed.add(displaySlice);
          }
        }
      }
    }
  }

  const [cropZ, cropY, cropX] = crop.cropShape;
  const [z0, y0, x0] = crop.offset;
  const cropBytes = crop.seg;

  for (let i = z0; i < z0 + cropZ; i++) {
    const displaySlice = crop.flipped ? ctx.sourceImageIds.length - 1 - i : i;
    const k = volumeKForDisplaySlice(ctx.vol, ctx.sourceImageIds, displaySlice);
    if (k < 0 || k >= ctx.nz) {
      continue;
    }

    const cropSliceBase = (i - z0) * cropY * cropX;
    const volumeSliceBase = k * ctx.sliceLen;
    let wrote = false;
    for (let cy = 0; cy < cropY; cy++) {
      const srcRow = cropSliceBase + cy * cropX;
      const dstRow = volumeSliceBase + (y0 + cy) * ctx.nx + x0;
      for (let cx = 0; cx < cropX; cx++) {
        const v = cropBytes[srcRow + cx];
        const dst = dstRow + cx;
        if (v) {
          if (ctx.arr[dst] === 0 || ctx.arr[dst] === segmentIndex) {
            if (ctx.arr[dst] !== segmentIndex) {
              ctx.arr[dst] = segmentIndex;
              wrote = true;
            }
            written.add(displaySlice);
          }
        } else if (crop.scope === 'delta' && ctx.arr[dst] === segmentIndex) {
          ctx.arr[dst] = 0;
          wrote = true;
        }
      }
    }
    if (wrote) {
      changed.add(displaySlice);
    }
  }

  ctx.vol.voxelManager.setCompleteScalarDataArray(ctx.arr);
  const changedSlices = Array.from(changed).sort((a, b) => a - b);
  const writtenSlices = Array.from(written).sort((a, b) => a - b);
  const nextDirty =
    crop.scope === 'delta'
      ? Array.from(new Set([...previousDirty.slices, ...changedSlices])).sort((a, b) => a - b)
      : writtenSlices;
  if (crop.scope !== 'delta' || previousDirty.known) {
    updateSegmentDirtyStats(segmentationId, segmentIndex, nextDirty);
  }

  return { changedSlices, wroteVoxels: writtenSlices.length > 0 };
}

function readObjectMaskFromVolume(
  servicesManager: any,
  source: SourceImage,
  segmentationId: string,
  segmentIndex: number
): Uint8Array | null {
  const ctx = getVolumeContext(servicesManager, segmentationId);
  if (!ctx) {
    failHard(`readObjectMask requires a native OHIF labelmap volume for ${segmentationId}#${segmentIndex}`);
  }
  if (source.imageIds.length !== ctx.sourceImageIds.length) {
    failHard(
      `readObjectMask source image count does not match labelmap volume for ${segmentationId}#${segmentIndex}`
    );
  }
  const mask = new Uint8Array(source.imageIds.length * ctx.sliceLen);
  let voxelCount = 0;
  for (let displaySlice = 0; displaySlice < source.imageIds.length; displaySlice++) {
    const k = volumeKForDisplaySlice(ctx.vol, ctx.sourceImageIds, displaySlice);
    if (k < 0 || k >= ctx.nz) {
      continue;
    }
    const src = k * ctx.sliceLen;
    const dst = displaySlice * ctx.sliceLen;
    for (let j = 0; j < ctx.sliceLen; j++) {
      if (ctx.arr[src + j] === segmentIndex) {
        mask[dst + j] = 1;
        voxelCount++;
      }
    }
  }
  return voxelCount > 0 ? mask : null;
}

function clearSegmentFromVolume(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number
): number[] | null {
  const ctx = getVolumeContext(servicesManager, segmentationId);
  if (!ctx) {
    return null;
  }

  const changed = new Set<number>();
  const previousDirty = getSegmentDirtySlices(segmentationId, segmentIndex);
  if (previousDirty.known) {
    for (const displaySlice of previousDirty.slices) {
      const k = volumeKForDisplaySlice(ctx.vol, ctx.sourceImageIds, displaySlice);
      if (k >= 0 && k < ctx.nz && clearObjectFromVolumeSlice(ctx, k, segmentIndex)) {
        changed.add(displaySlice);
      }
    }
  } else {
    for (let k = 0; k < ctx.nz; k++) {
      if (clearObjectFromVolumeSlice(ctx, k, segmentIndex)) {
        const displaySlice = displaySliceForVolumeK(ctx.vol, ctx.sourceImageIds, k);
        if (displaySlice >= 0) {
          changed.add(displaySlice);
        }
      }
    }
  }
  ctx.vol.voxelManager.setCompleteScalarDataArray(ctx.arr);
  return Array.from(changed).sort((a, b) => a - b);
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
  return readObjectMaskFromVolume(servicesManager, source, segmentationId, segmentIndex);
}

/** Zero all voxels belonging to an object segment (reset). Returns the changed slices. */
export async function clearSegment(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number
): Promise<void> {
  await ensureNativeLabelmapVolume(servicesManager, segmentationId);
  const volumeChanged = clearSegmentFromVolume(servicesManager, segmentationId, segmentIndex);
  if (volumeChanged) {
    updateSegmentDirtyStats(segmentationId, segmentIndex, []);
    flushAuthoritativeLabelmap(servicesManager, segmentationId, 'volumeToStack', volumeChanged);
    if (await mprReadyForGlobalDispatch(servicesManager, segmentationId)) {
      dispatchModified(segmentationId);
    }
    return;
  }

  failHard(`clearSegment requires a native OHIF labelmap volume for ${segmentationId}#${segmentIndex}`);
}

/** Remove an object segment entirely (clear voxels + drop the segment entry). */
export async function removeSegment(
  servicesManager: any,
  segmentationId: string,
  segmentIndex: number
): Promise<void> {
  await clearSegment(servicesManager, segmentationId, segmentIndex);
  const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
  const segments = { ...(seg?.segments ?? {}) };
  delete segments[segmentIndex];
  csToolsSegmentation.updateSegmentations([{ segmentationId, payload: { segments } }]);
  if (await mprReadyForGlobalDispatch(servicesManager, segmentationId)) {
    dispatchModified(segmentationId);
  }
}

export function markMprDirty(segmentationId: string): void {
  mprDirtySegIds.add(segmentationId);
}

export function isMprDirty(segmentationId: string): boolean {
  return mprDirtySegIds.has(segmentationId);
}

export function getMprDirtySegIds(): string[] {
  return Array.from(mprDirtySegIds);
}

export function getManagedSegmentationIds(): string[] {
  return Array.from(managedSegIds).filter(segmentationId =>
    !!csToolsSegmentation.state.getSegmentation(segmentationId)
  );
}

/**
 * Volume-viewport guard: after OHIF has attached source volumes, validate native
 * labelmap state for managed segmentations and strip representations from 3D panes.
 */
export async function ensureMprForManagedSegmentations(servicesManager: any): Promise<void> {
  const { mpr, pendingMpr, volume3d } = classifyViewports(servicesManager);
  const service = servicesManager.services.segmentationService;
  logPendingMprOnce(pendingMpr);

  for (const segmentationId of managedSegIds) {
    if (!csToolsSegmentation.state.getSegmentation(segmentationId)) {
      continue;
    }
    for (const viewportId of volume3d) {
      try {
        service.removeSegmentationRepresentations(viewportId, { segmentationId });
      } catch {
        // ignore
      }
    }
    if (!mpr.length) {
      continue;
    }

    ensureNativeVolumeReferenceForMpr(servicesManager, segmentationId);
    const missing = getRepresentationsMissing(servicesManager, segmentationId, mpr);
    if (!missing.length && !mprDirtySegIds.has(segmentationId)) {
      continue;
    }
    await ensureMprRepresentations(servicesManager, segmentationId, mpr);
    if (missing.length || mprDirtySegIds.has(segmentationId)) {
      dispatchModified(segmentationId);
    }
  }
}
