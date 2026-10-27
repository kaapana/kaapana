// coordinateMapping: the single, testable path for all prompt coordinate conversion.
//
// Tools produce world geometry on Cornerstone annotations; this module converts it to
// source display-set voxel coordinates [x, y, slice] — the order the proxy expects.
// For stack viewports the slice is the referenced image-id index; for MPR/volume
// viewports the world point is mapped to volume IJK and the volume slice id is mapped
// back through the source display-set image-id order (the robust MPR rule).
//
// Coordinates stay unrounded, like napari's data coordinates: the proxy applies the
// napari-nninteractive plugin's own rounding, brush and polygon rules. Only the axis of
// the drawn plane is snapped to the displayed slice, as a napari layer lies on one slice.
//
// No command or tool builds IJK directly; everything goes through here.

import { BaseVolumeViewport, VolumeViewport3D, utilities as csUtils } from '@cornerstonejs/core';

import { FreehandPrompt, ViewportKind } from './types';

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

/**
 * Convert a single world point to source display-set voxel coordinates [x, y, slice].
 * `dsImageIds` is the source display-set image-id order; `referencedImageId` is the
 * annotation's slice for stack viewports.
 */
function worldToSourceVoxel(
  viewport: any,
  world: number[],
  dsImageIds: string[],
  referencedImageId?: string
): [number, number, number] | undefined {
  const imageData = getImageData(viewport);
  if (!imageData) {
    return undefined;
  }
  const [x, y, k] = csUtils.transformWorldToIndex(imageData, world as any);

  if (viewport instanceof BaseVolumeViewport) {
    const volumeImageIds: string[] = viewport.getImageIds?.() ?? [];
    const kRounded = Math.min(Math.max(Math.round(k), 0), Math.max(volumeImageIds.length - 1, 0));
    let z = k;
    if (dsImageIds?.length && volumeImageIds.length) {
      const idx = dsImageIds.indexOf(volumeImageIds[kRounded]);
      if (idx >= 0) {
        // Keep the sub-slice fraction; it runs backwards when the volume's slice order is
        // the reverse of the display set's.
        const first = dsImageIds.indexOf(volumeImageIds[0]);
        const last = dsImageIds.indexOf(volumeImageIds[volumeImageIds.length - 1]);
        const direction = last >= first ? 1 : -1;
        z = idx + direction * (k - kRounded);
      }
    }
    return [x, y, z];
  }

  // Stack viewport: the slice is the referenced image id's position in source order.
  let z = Math.round(k);
  if (referencedImageId && dsImageIds?.length) {
    const idx = dsImageIds.indexOf(referencedImageId);
    if (idx >= 0) {
      z = idx;
    }
  }
  return [x, y, z];
}

/** World polyline of an annotation: probe/rectangle handles or a freehand contour. */
function promptWorldPoints(annotation: any): number[][] {
  const { handles, contour } = annotation.data ?? {};
  return handles?.points?.length ? handles.points : (contour?.polyline ?? []);
}

function convertAll(viewport: any, annotation: any, dsImageIds: string[]): number[][] {
  const referencedImageId = annotation.metadata?.referencedImageId;
  return promptWorldPoints(annotation)
    .map(p => worldToSourceVoxel(viewport, p, dsImageIds, referencedImageId))
    .filter(Boolean) as number[][];
}

/** Points of one prompt, with the drawn plane's axis snapped to the displayed slice. */
function convertOnPlane(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): { points: number[][]; axis: number | undefined } {
  const points = convertAll(viewport, annotation, dsImageIds);
  const axis = points.length
    ? (planeAxisFromViewport(viewport) ?? planeAxisFromPoints(points))
    : undefined;
  if (axis !== undefined) {
    const slice = Math.round(points[0][axis]);
    for (const point of points) {
      point[axis] = slice;
    }
  }
  return { points, axis };
}

function indexToWorld(imageData: any, index: number[]): number[] | undefined {
  return imageData?.indexToWorld?.(index) ?? csUtils.transformIndexToWorld(imageData, index as any);
}

function normalize(vector: number[]): number[] | undefined {
  const length = Math.hypot(vector[0], vector[1], vector[2]);
  if (!Number.isFinite(length) || length === 0) {
    return undefined;
  }
  return vector.map(v => v / length);
}

function dot(a: number[], b: number[]): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function planeAxisFromViewport(viewport: any): number | undefined {
  // Stack annotations are always on one displayed source slice.
  if (!(viewport instanceof BaseVolumeViewport)) {
    return 2;
  }

  const imageData = getImageData(viewport);
  const normal = normalize(Array.from(viewport.getCamera?.()?.viewPlaneNormal ?? []) as number[]);
  const origin = indexToWorld(imageData, [0, 0, 0]);
  if (!normal || !origin) {
    return undefined;
  }

  const scores = [0, 1, 2].map(axis => {
    const unit = [0, 0, 0];
    unit[axis] = 1;
    const world = indexToWorld(imageData, unit);
    if (!world) {
      return -1;
    }
    const axisVector = normalize(world.map((value, i) => value - origin[i]));
    return axisVector ? Math.abs(dot(normal, axisVector)) : -1;
  });
  const best = scores.reduce((acc, score, axis) => (score > acc.score ? { axis, score } : acc), {
    axis: -1,
    score: -1,
  });
  return best.axis >= 0 && best.score > 0 ? best.axis : undefined;
}

function planeAxisFromPoints(points: number[][]): number | undefined {
  if (!points.length) {
    return undefined;
  }
  const ranges = [0, 1, 2].map(axis => {
    const values = points.map(point => point[axis]);
    return Math.max(...values) - Math.min(...values);
  });
  // Prefer the source slice axis on ties; it matches stack prompts and avoids
  // treating an axis-aligned in-plane stroke as a sagittal/coronal mask.
  return [2, 1, 0].reduce((best, axis) => (ranges[axis] < ranges[best] ? axis : best), 2);
}

/** Point prompt (Probe2) → [x, y, slice]. */
export function pointIJK(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): number[] | undefined {
  return convertOnPlane(viewport, annotation, dsImageIds).points[0];
}

/**
 * Box prompt (RectangleROI2) → [[minX, minY, minZ], [maxX, maxY, maxZ]] over its corners.
 * The proxy turns this into napari's half-open box (the collapsed plane axis gets +1).
 */
export function boxIJK(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): number[][] | undefined {
  const { points } = convertOnPlane(viewport, annotation, dsImageIds);
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

/** Freehand prompt (scribble or lasso) → polyline of [x, y, slice] plus the drawn plane's axis. */
export function freehandIJK(
  viewport: any,
  annotation: any,
  dsImageIds: string[]
): FreehandPrompt | undefined {
  const { points, axis } = convertOnPlane(viewport, annotation, dsImageIds);
  if (!points.length) {
    return undefined;
  }
  return { points, axis };
}
