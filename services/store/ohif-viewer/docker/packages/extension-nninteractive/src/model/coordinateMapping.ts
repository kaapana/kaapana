// coordinateMapping: the single, testable path for all prompt coordinate conversion.
//
// Tools produce world geometry on Cornerstone annotations; this module converts it to
// source display-set voxel coordinates [x, y, slice] — the order the proxy expects.
// For stack viewports the slice is the referenced image-id index; for MPR/volume
// viewports the world point is mapped to volume IJK and the volume slice id is mapped
// back through the source display-set image-id order (the robust MPR rule).
//
// No command or tool builds IJK directly; everything goes through here.

import {
  BaseVolumeViewport,
  VolumeViewport3D,
  utilities as csUtils,
} from '@cornerstonejs/core';

import { ViewportKind } from './types';

function getImageData(viewport: any): any {
  const image = viewport?.getImageData?.();
  return image?.imageData ?? image;
}

export function viewportKind(viewport: any): ViewportKind {
  if (!viewport) {
    return 'unsupported';
  }
  if (viewport instanceof VolumeViewport3D) {
    return 'volume3d';
  }
  if (viewport instanceof BaseVolumeViewport) {
    return 'volumeMpr';
  }
  return 'stack';
}

export function isPromptableViewport(viewport: any): boolean {
  const kind = viewportKind(viewport);
  return kind === 'stack' || kind === 'volumeMpr';
}

/**
 * Convert a single world point to source display-set voxel coordinates [x, y, slice].
 * `dsImageIds` is the source display-set image-id order; `referencedImageId` is the
 * annotation's slice for stack viewports.
 */
export function worldToSourceVoxel(
  viewport: any,
  world: number[],
  dsImageIds: string[],
  referencedImageId?: string
): [number, number, number] | undefined {
  const imageData = getImageData(viewport);
  if (!imageData || typeof csUtils.transformWorldToIndex !== 'function') {
    return undefined;
  }
  const ijk = csUtils.transformWorldToIndex(imageData, world as any);
  if (!ijk) {
    return undefined;
  }
  const x = Math.round(ijk[0]);
  const y = Math.round(ijk[1]);

  if (viewport instanceof BaseVolumeViewport) {
    const k = Math.round(ijk[2]);
    const volumeImageIds: string[] = viewport.getImageIds?.() ?? [];
    const srcImageId = volumeImageIds[k];
    let z = k;
    if (srcImageId && dsImageIds?.length) {
      const idx = dsImageIds.indexOf(srcImageId);
      if (idx >= 0) {
        z = idx;
      }
    }
    return [x, y, z];
  }

  // Stack viewport: the slice is the referenced image id's position in source order.
  let z = Math.round(ijk[2]);
  if (referencedImageId && dsImageIds?.length) {
    const idx = dsImageIds.indexOf(referencedImageId);
    if (idx >= 0) {
      z = idx;
    }
  }
  return [x, y, z];
}

/** World polyline of an annotation, regardless of tool (points, rectangle corners, contour). */
export function getPromptWorldPoints(annotation: any): number[][] {
  const data = annotation?.data ?? {};
  if (Array.isArray(data.handles?.points) && data.handles.points.length) {
    return data.handles.points;
  }
  if (Array.isArray(data.contour?.polyline) && data.contour.polyline.length) {
    return data.contour.polyline;
  }
  if (Array.isArray(data.polyline) && data.polyline.length) {
    return data.polyline;
  }
  return [];
}

function convertAll(viewport: any, annotation: any, dsImageIds: string[]): number[][] {
  const referencedImageId = annotation?.metadata?.referencedImageId;
  return getPromptWorldPoints(annotation)
    .map(p => worldToSourceVoxel(viewport, p, dsImageIds, referencedImageId))
    .filter(Boolean) as number[][];
}

/** Point prompt (Probe2) → [x, y, slice]. */
export function pointIJK(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): number[] | undefined {
  const points = convertAll(viewport, annotation, dsImageIds);
  return points[0];
}

/** Box prompt (RectangleROI2) → [[minX, minY, minZ], [maxX, maxY, maxZ]]. */
export function boxIJK(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): number[][] | undefined {
  const points = convertAll(viewport, annotation, dsImageIds);
  if (points.length < 2) {
    return undefined;
  }
  const xs = points.map(p => p[0]);
  const ys = points.map(p => p[1]);
  const zs = points.map(p => p[2]);
  return [
    [Math.min(...xs), Math.min(...ys), Math.min(...zs)],
    [Math.max(...xs), Math.max(...ys), Math.max(...zs)],
  ];
}

/** Freehand prompt (scribble or lasso) → polyline of [x, y, slice]. */
export function freehandIJK(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): number[][] | undefined {
  const points = convertAll(viewport, annotation, dsImageIds);
  return points.length ? points : undefined;
}
