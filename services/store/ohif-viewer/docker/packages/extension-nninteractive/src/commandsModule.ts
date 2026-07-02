import dcmjs from 'dcmjs';
import { DicomMetadataStore, utils, Types } from '@ohif/core';
import {
  Enums as csToolsEnums,
  Types as cstTypes,
  segmentation as csToolsSegmentation,
} from '@cornerstonejs/tools';
import * as cornerstoneTools from '@cornerstonejs/tools';
import {
  cache,
  imageLoader,
  metaData,
  volumeLoader,
  Types as csTypes,
  utilities as csUtils,
  BaseVolumeViewport,
  VolumeViewport3D,
  eventTarget,
} from '@cornerstonejs/core';
import { adaptersSEG, helpers } from '@cornerstonejs/adapters';
import { createReportDialogPrompt } from '@ohif/extension-default';
import axios from 'axios';

import PROMPT_RESPONSES from '../../default/src/utils/_shared/PROMPT_RESPONSES';
import { updateSegmentationStats } from '../../cornerstone/src/utils/updateSegmentationStats';
import { updateSegmentBidirectionalStats } from '../../cornerstone/src/utils/updateSegmentationStats';
import { useSegmentationPresentationStore } from '../../cornerstone/src/stores';
import { toolboxState } from './utils/toolboxState';
import { parseMultipart } from './utils/multipart';
import { dispatchMeasurementStateChanged } from './utils/measurementStateChanged';

const LABELMAP = csToolsEnums.SegmentationRepresentations.Labelmap;
const { downloadDICOMData } = helpers;
const {
  Cornerstone3D: {
    Segmentation: { generateSegmentation: generateSEGFromLabelmap },
  },
} = adaptersSEG;

/** Tracks the last series initialized by initNninter to detect study/series changes. */
let _lastInitSeries: string | undefined = undefined;
let _nnInteractiveClientSessionId: string | undefined = undefined;
let _pendingInitKey: string | undefined = undefined;
let _pendingInitPromise: Promise<any> | undefined = undefined;
const NNINTERACTIVE_CLIENT_SESSION_KEY = 'kaapana.nninteractive.clientSessionId';

/**
 * A 409 from the nnInteractive proxy means the backend session is gone (never
 * initialized, or reaped after the idle/liveness timeout). Mark it inactive so
 * the AI toolbox re-gates prompts until the user clicks Initialize again.
 */
function _isSessionExpiredError(error: any): boolean {
  return error?.response?.status === 409;
}

/** Safely parse a numeric timing field from multipart response metadata. */
function metaNum(meta: Record<string, unknown>, key: string): number | undefined {
  const v = meta[key];
  if (v === undefined || v === null) return undefined;
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return isFinite(n) ? n : undefined;
}

function getNnInteractiveClientSessionId(): string {
  if (_nnInteractiveClientSessionId) {
    return _nnInteractiveClientSessionId;
  }

  try {
    const stored = globalThis?.sessionStorage?.getItem(NNINTERACTIVE_CLIENT_SESSION_KEY);
    if (stored) {
      _nnInteractiveClientSessionId = stored;
      return stored;
    }
  } catch {
    // sessionStorage is unavailable in some embedded/private contexts.
  }

  const id =
    globalThis?.crypto?.randomUUID?.() ??
    `nninteractive-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  _nnInteractiveClientSessionId = id;

  try {
    globalThis?.sessionStorage?.setItem(NNINTERACTIVE_CLIENT_SESSION_KEY, id);
  } catch {
    // Best effort only; the in-memory id still isolates this JS runtime.
  }

  return id;
}

function withNnInteractiveClientSession(url: string): string {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}clientSessionID=${encodeURIComponent(getNnInteractiveClientSessionId())}`;
}

function constructInferenceFormData(params: Record<string, unknown>, files?: any[] | null) {
  const formData = new FormData();
  formData.append(
    'params',
    JSON.stringify({
      ...params,
      clientSessionID: params.clientSessionID ?? getNnInteractiveClientSessionId(),
    })
  );

  if (files) {
    const fileList = Array.isArray(files) ? files : [files];
    for (const file of fileList) {
      formData.append(file.name, file.data, file.fileName);
    }
  }

  return formData;
}

function getClosedFreehandBoundaryIJK(
  measurement: any,
  viewport: any,
  displaySetImageIds?: string[]
): number[][] | undefined {
  const isVolume = viewport instanceof BaseVolumeViewport;
  const dataValues = Object.values(measurement?.data ?? {});
  // The patched-tool cached payload is only trusted for stack viewports — its volumeId branch is
  // unreliable (depends on a global `services`) and was the source of mis-placed MPR segments.
  if (!isVolume) {
    const cachedBoundary = dataValues.find((value: any) => value?.boundary?.length)?.boundary;
    if (cachedBoundary?.length) {
      return cachedBoundary.map((point: number[]) => point.map(value => Math.round(value)));
    }
  }

  const worldPoints =
    measurement?.points ??
    measurement?.data?.contour?.polyline ??
    dataValues.find((value: any) => value?.points?.length)?.points ??
    dataValues.find((value: any) => value?.polyline?.length)?.polyline;

  if (!worldPoints?.length) {
    return undefined;
  }

  const ijkPoints = worldPoints
    .map((point: number[]) => worldToIJKForMeasurement(point, measurement, viewport, displaySetImageIds))
    .filter(Boolean) as number[][];

  return ijkPoints.length ? ijkPoints : undefined;
}

function getMeasurementWorldPoints(measurement: any): number[][] {
  const candidates = [
    measurement?.points,
    measurement?.data?.handles?.points,
    measurement?.data?.contour?.polyline,
    ...Object.values(measurement?.data ?? {}).flatMap((value: any) => [
      value?.points,
      value?.polyline,
      value?.handles?.points,
      value?.contour?.polyline,
    ]),
  ];

  for (const candidate of candidates) {
    if (!Array.isArray(candidate) || candidate.length === 0) {
      continue;
    }

    const points = candidate
      .filter(point => Array.isArray(point) && point.length >= 3)
      .map(point => point.slice(0, 3).map(Number))
      .filter(point => point.every(Number.isFinite));

    if (points.length > 0) {
      return points;
    }
  }

  return [];
}

/**
 * Convert a world point to the [x, y, z] index the nnInteractive proxy expects, for ANY draw plane.
 *
 * - STACK viewport: getImageData().imageData is the single displayed slice ([cols,rows,1]); x/y come
 *   from it and z is the slice's index within the stack (via referencedImageId).
 * - VOLUME / MPR viewport: getImageData().imageData is the full 3D volume; transformWorldToIndex gives
 *   the full volume index [i=col, j=row, k=slice] for the point regardless of which plane it was drawn
 *   on. The proxy expects z in the SOURCE display-set (InstanceNumber) slice order — the same convention
 *   the known-correct axial-stack path uses — NOT the volume's geometric k order. We convert by looking
 *   up the source imageId at volume slice k in the display-set order: z = displaySetImageIds.indexOf(
 *   volumeImageIds[k]). This reduces to the working axial invariant and needs no flip guessing.
 */
function worldToIJKForMeasurement(
  point: number[],
  measurement: any,
  viewport: any,
  displaySetImageIds?: string[]
): number[] | undefined {
  const imageData = viewport?.getImageData?.()?.imageData ?? viewport?.getImageData?.();
  if (!imageData || !csUtils.transformWorldToIndex) {
    return;
  }

  const ijk = csUtils.transformWorldToIndex(imageData, point);
  if (!ijk?.length || !ijk.every(Number.isFinite)) {
    return;
  }

  const x = Math.round(ijk[0]);
  const y = Math.round(ijk[1]);

  if (viewport instanceof BaseVolumeViewport) {
    // Volume / MPR: map the volume slice k → source display-set (stack) index.
    const k = Math.round(ijk[2]);
    const volumeImageIds: string[] = viewport?.getImageIds?.() ?? [];
    let z = k;
    const srcImageId = volumeImageIds[k];
    if (srcImageId && displaySetImageIds?.length) {
      const stackIdx = displaySetImageIds.indexOf(srcImageId);
      if (stackIdx >= 0) {
        z = stackIdx;
      } else {
        console.debug(
          `[nninter] worldToIJK volume: imageId at volume k=${k} not found in display-set order; using raw k=${k}`
        );
      }
    } else if (!displaySetImageIds?.length) {
      console.debug('[nninter] worldToIJK volume: no displaySetImageIds passed; using raw volume k for z');
    }
    return [x, y, z];
  }

  // Stack viewport: z is the drawn slice's index within the stack.
  const viewportImageIds = viewport?.getImageIds?.() ?? [];
  const referencedSliceIndex = viewportImageIds.indexOf(measurement?.referencedImageId);
  return [x, y, referencedSliceIndex >= 0 ? referencedSliceIndex : Math.round(ijk[2])];
}

function getPromptPointIJK(
  measurement: any,
  viewport: any,
  displaySetImageIds?: string[]
): number[] | undefined {
  // Trust the patched-tool cached index only for stack viewports (see note in getClosedFreehandBoundaryIJK).
  if (!(viewport instanceof BaseVolumeViewport)) {
    const cachedIndex = Object.values(measurement?.data ?? {}).find(
      (value: any) => value?.index?.length === 3
    ) as any;
    if (cachedIndex?.index?.length === 3) {
      return cachedIndex.index.map((value: number) => Math.round(value));
    }
  }

  const [worldPoint] = getMeasurementWorldPoints(measurement);
  return worldPoint ? worldToIJKForMeasurement(worldPoint, measurement, viewport, displaySetImageIds) : undefined;
}

function getRectangleBoxIJK(
  measurement: any,
  viewport: any,
  displaySetImageIds?: string[]
): number[][] | undefined {
  if (!(viewport instanceof BaseVolumeViewport)) {
    const cachedPoints = Object.values(measurement?.data ?? {}).find(
      (value: any) => value?.pointsInShape?.length
    ) as any;
    if (cachedPoints?.pointsInShape?.length) {
      return [cachedPoints.pointsInShape.at(0).pointIJK, cachedPoints.pointsInShape.at(-1).pointIJK];
    }
  }

  const ijkPoints = getMeasurementWorldPoints(measurement)
    .map(point => worldToIJKForMeasurement(point, measurement, viewport, displaySetImageIds))
    .filter(Boolean) as number[][];

  if (ijkPoints.length === 0) {
    return;
  }

  // 3D bounding box over ALL corners — for off-axial (sagittal/coronal) boxes the corners span a
  // z-range, so z must NOT be collapsed to a single slice. For axial boxes min==max z (unchanged).
  const xValues = ijkPoints.map(point => point[0]);
  const yValues = ijkPoints.map(point => point[1]);
  const zValues = ijkPoints.map(point => point[2]);

  return [
    [Math.min(...xValues), Math.min(...yValues), Math.min(...zValues)],
    [Math.max(...xValues), Math.max(...yValues), Math.max(...zValues)],
  ];
}

function getOpenFreehandIJK(
  measurement: any,
  viewport: any,
  displaySetImageIds?: string[]
): number[][] | undefined {
  if (!(viewport instanceof BaseVolumeViewport)) {
    const cachedScribble = Object.values(measurement?.data ?? {}).find(
      (value: any) => value?.scribble?.length
    ) as any;
    if (cachedScribble?.scribble?.length) {
      return cachedScribble.scribble.map((point: number[]) => point.map(value => Math.round(value)));
    }
  }

  const ijkPoints = getMeasurementWorldPoints(measurement)
    .map(point => worldToIJKForMeasurement(point, measurement, viewport, displaySetImageIds))
    .filter(Boolean) as number[][];

  return ijkPoints.length ? ijkPoints : undefined;
}



const commandsModule = ({
  servicesManager,
  commandsManager,
  extensionManager,
}: Types.Extensions.ExtensionParams): Types.Extensions.CommandsModule => {
  const {
    customizationService,
    measurementService,
    uiNotificationService,
    viewportGridService,
    displaySetService,
    segmentationService,
    cornerstoneViewportService,
    toolGroupService,
  } = servicesManager.services;

  const aiPromptToolNames = ['Probe2', 'PlanarFreehandROI2', 'PlanarFreehandROI3', 'RectangleROI2'];
  const pendingLivePrompts = new Map<string, { unsubscribe?: () => void; rafId?: number }>();

  // ── MPR manual-correction sync state ──────────────────────────────────────────────────────────
  // The MPR overlay is a derived labelmap VOLUME (display copy); the per-slice stack labelmap is the
  // source of truth for DICOM-SEG export/store. A manual brush in an MPR viewport edits the VOLUME,
  // so we track that the volume has unsynced edits and copy them back into the stack labelmap before
  // export. _mprRefVolumeIdBySeg remembers each segmentation's source CT volumeId for the reverse map.
  const _mprRefVolumeIdBySeg = new Map<string, string>();
  // Segmentations whose MPR volume has unsynced brush edits (each object is its own segmentation, so
  // several may be dirty before export). Synced back verbatim (1:1) at export time.
  const _mprDirtySegIds = new Set<string>();

  // ── Per-object (overlap) model ───────────────────────────────────────────────────────────────
  // Each object is its OWN Cornerstone segmentation: a single segment (index 1) in a single S-image
  // stack labelmap holding value 1, plus its own derived labelmap VOLUME for MPR. Overlap is native
  // — Cornerstone renders one actor per segmentation (stack and volume), so two objects marking the
  // same voxel simply layer. Export packs all sibling segmentations into ONE overlapping DICOM SEG;
  // import splits a hydrated multi-segment SEG back into per-object segmentations (see
  // maybeSplitHydratedSegmentation), so authoring and import converge on the same shape and
  // round-trip cleanly.
  //
  // The nnInteractive proxy tracks ONE object per session, so we remember which OBJECT the backend
  // currently holds (segmentationId#1) and drive reset_first / set_mask from it.
  let _serverObjectId: string | undefined; // `${segmentationId}#${segmentIndex}` or undefined (blank)
  const serverObjKey = (segId: string, segIdx: number) => `${segId}#${segIdx}`;
  const _objectSegmentationIdsBySeries = new Map<string, string[]>();
  // Segmentations WE own (created by inference or by the import-split). The import-split guard uses
  // this to ignore its own SEGMENTATION_ADDED events and to skip already-per-object segmentations.
  const _nninterManagedSegIds = new Set<string>();
  // Hydrated originals that were split into per-object segmentations. Their STATE is kept (OHIF's
  // presentation store / SEG-displaySet link / toolbar evaluators reference it — deleting it crashes
  // the viewer), but their representations are stripped and they are excluded from object discovery,
  // export, and the MPR guard.
  const _splitConsumedIds = new Set<string>();

  const rememberObjectSegmentation = (seriesUID: string | undefined, segmentationId: string | undefined) => {
    if (!seriesUID || !segmentationId) {
      return;
    }

    const ids = _objectSegmentationIdsBySeries.get(seriesUID) ?? [];
    if (!ids.includes(segmentationId)) {
      ids.push(segmentationId);
      _objectSegmentationIdsBySeries.set(seriesUID, ids);
    }
  };

  const getSegmentationStateById = (segmentationId: string | undefined): any => {
    if (!segmentationId) {
      return undefined;
    }

    const csSeg = csToolsSegmentation.state.getSegmentation(segmentationId);
    const serviceSeg = segmentationService.getSegmentation(segmentationId);
    if (!csSeg) {
      return serviceSeg;
    }
    if (!serviceSeg) {
      return csSeg;
    }

    return {
      ...serviceSeg,
      ...csSeg,
      cachedStats: {
        ...(serviceSeg.cachedStats ?? {}),
        ...(csSeg.cachedStats ?? {}),
      },
      representationData: {
        ...(serviceSeg.representationData ?? {}),
        ...(csSeg.representationData ?? {}),
      },
      segments: {
        ...(serviceSeg.segments ?? {}),
        ...(csSeg.segments ?? {}),
      },
    };
  };

  /** The source (CT) SeriesInstanceUID a segmentation was authored on / imported for, or undefined. */
  const segSeriesUID = (seg: any): string | undefined => {
    if (!seg) return undefined;
    if (seg.cachedStats?.seriesInstanceUid) return seg.cachedStats.seriesInstanceUid;
    for (const s of Object.values(seg.segments ?? {}) as any[]) {
      if (s?.cachedStats?.algorithmName) return s.cachedStats.algorithmName;
    }
    const refIds: string[] = (seg.representationData?.[LABELMAP] as any)?.referencedImageIds ?? [];
    if (refIds[0]) {
      const inst: any = metaData.get('instance', refIds[0]);
      if (inst?.SeriesInstanceUID) return inst.SeriesInstanceUID;
    }
    return undefined;
  };

  const segReferencedImageIds = (seg: any): string[] => {
    const lm: any = seg?.representationData?.[LABELMAP];
    if (lm?.referencedImageIds?.length) {
      return lm.referencedImageIds;
    }

    const imageIds: string[] = lm?.imageIds ?? [];
    return imageIds
      .map(imageId => cache.getImage(imageId)?.referencedImageId)
      .filter(Boolean);
  };

  const sameReferencedImageStack = (a: string[] = [], b: string[] = []): boolean => {
    if (!a.length || !b.length || a.length !== b.length) {
      return false;
    }

    return a[0] === b[0] && a[a.length - 1] === b[b.length - 1];
  };

  const allSegmentationStates = (): any[] => {
    const byId = new Map<string, any>();
    const add = (seg: any) => {
      if (!seg?.segmentationId) {
        return;
      }

      const previous = byId.get(seg.segmentationId) ?? {};
      byId.set(seg.segmentationId, {
        ...previous,
        ...seg,
        cachedStats: {
          ...(previous.cachedStats ?? {}),
          ...(seg.cachedStats ?? {}),
        },
        representationData: {
          ...(previous.representationData ?? {}),
          ...(seg.representationData ?? {}),
        },
        segments: {
          ...(previous.segments ?? {}),
          ...(seg.segments ?? {}),
        },
      });
    };

    ((csToolsSegmentation.state.getSegmentations?.() ?? []) as any[]).forEach(add);
    ((segmentationService.getSegmentations?.() ?? []) as any[]).forEach(add);
    for (const ids of _objectSegmentationIdsBySeries.values()) {
      ids.map(getSegmentationStateById).forEach(add);
    }
    try {
      const viewportIds = cornerstoneViewportService.getViewportIds?.() ?? [];
      for (const viewportId of viewportIds) {
        const reps =
          (segmentationService as any).getSegmentationRepresentations?.(viewportId) ?? [];
        reps.map((rep: any) => getSegmentationStateById(rep?.segmentationId)).forEach(add);
      }
    } catch (error) {
      console.warn('[nninter] could not scan viewport segmentation representations:', error);
    }

    return Array.from(byId.values());
  };

  /** True if a segmentation is an nnInteractive object for the given source series. */
  const segBelongsToSeries = (
    seg: any,
    seriesUID: string,
    sourceImageIds: string[] = []
  ): boolean => {
    if (!seriesUID) {
      return false;
    }

    if (segSeriesUID(seg) === seriesUID) {
      return true;
    }

    const refIds = segReferencedImageIds(seg);
    if (sameReferencedImageStack(refIds, sourceImageIds)) {
      return true;
    }

    const firstRef = refIds[0];
    const inst: any = firstRef ? metaData.get('instance', firstRef) : undefined;
    return inst?.SeriesInstanceUID === seriesUID;
  };

  /** All segmentations (objects) that belong to a given source series. */
  const seriesSegmentations = (seriesUID: string, sourceImageIds: string[] = []): any[] => {
    const byId = new Map<string, any>();
    const addIfBelongs = (seg: any) => {
      if (!seg?.segmentationId) {
        return;
      }
      // A split-consumed hydrated original is kept in state for OHIF's bookkeeping but is NOT an
      // object — exclude it from discovery (export siblings, refine resolution, ordinals).
      if (_splitConsumedIds.has(seg.segmentationId)) {
        return;
      }
      if (segBelongsToSeries(seg, seriesUID, sourceImageIds)) {
        byId.set(seg.segmentationId, seg);
      }
    };

    (_objectSegmentationIdsBySeries.get(seriesUID) ?? [])
      .map(getSegmentationStateById)
      .forEach(addIfBelongs);
    allSegmentationStates().forEach(addIfBelongs);

    return Array.from(byId.values());
  };

  const objectColorPalette = [
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

  const objectColorForOrdinal = (ordinal: number | undefined): number[] => {
    const index = Math.max(0, (ordinal ?? 1) - 1) % objectColorPalette.length;
    return objectColorPalette[index];
  };

  const getObjectSegmentColor = (
    segmentation: any,
    segmentIndex: number
  ): number[] | undefined => {
    const segment = segmentation?.segments?.[segmentIndex];
    return segment?.cachedStats?.color || segment?.color;
  };

  const setObjectSegmentColor = (
    segmentationId: string,
    segmentIndex: number,
    color: number[] | undefined,
    viewportIds: string[]
  ) => {
    const setSegmentColor = (segmentationService as any)?.setSegmentColor;
    if (!color || typeof setSegmentColor !== 'function') {
      return;
    }

    for (const viewportId of viewportIds) {
      try {
        setSegmentColor.call(segmentationService, viewportId, segmentationId, segmentIndex, color);
      } catch (error) {
        console.warn(`[nninter] could not set object color for ${segmentationId} in ${viewportId}:`, error);
      }
    }
  };

  // Force every viewport to render INACTIVE segmentations. In the per-object model each object is its
  // own segmentation and only ONE is active per viewport, so without this only the active object would
  // show. cs-tools defaults this to true on first rep-add, but OHIF's panel can turn it off — set it
  // explicitly so all objects (and their overlap) always render in stack AND MPR.
  const enableRenderInactiveSegmentations = (viewportIds: string[]) => {
    const style: any = (csToolsSegmentation as any).segmentationStyle;
    if (!style?.setRenderInactiveSegmentations) {
      return;
    }
    for (const viewportId of viewportIds) {
      try {
        style.setRenderInactiveSegmentations(viewportId, true);
      } catch (error) {
        console.warn(`[nninter] could not enable render-inactive for ${viewportId}:`, error);
      }
    }
  };

  const getCurrentStackImageIdIndex = (viewportId: string): number | undefined => {
    try {
      const viewport = servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(viewportId);
      if (!viewport || viewport instanceof BaseVolumeViewport) {
        return undefined;
      }
      return viewport.getCurrentImageIdIndex?.();
    } catch (error) {
      console.warn(`[nninter] could not read stack image index for ${viewportId}:`, error);
      return undefined;
    }
  };

  /** Get the labelmap volumeId used for the MPR overlay of a segmentation. */
  const mprLabelmapVolumeId = (segmentationId: string) => `${segmentationId}-mpr-labelmap`;

  /**
   * Copy the MPR labelmap VOLUME back into the per-slice STACK labelmap images (the inverse of
   * buildAndSyncLabelmapVolume), so manual brush corrections done in MPR persist to DICOM-SEG
   * export/store and the stack view. Geometric, guarded; no-op (returns false) if there is no
   * volume labelmap or the geometry can't be resolved.
   */
  const syncVolumeLabelmapToStack = (segmentationId: string): boolean => {
    try {
      const labelmapVol: any = cache.getVolume(mprLabelmapVolumeId(segmentationId));
      if (!labelmapVol?.voxelManager?.getCompleteScalarDataArray) {
        return false;
      }
      const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
      const stackImageIds: string[] = (seg?.representationData?.[LABELMAP] as any)?.imageIds ?? [];
      if (!stackImageIds.length) {
        return false;
      }
      const refVolumeId: string | undefined =
        labelmapVol.referencedVolumeId || _mprRefVolumeIdBySeg.get(segmentationId);
      const srcVol: any = refVolumeId ? cache.getVolume(refVolumeId) : null;
      const srcVolImageIds: string[] = srcVol?.imageIds ?? [];
      if (!srcVolImageIds.length) {
        console.warn('[nninter] sync volume→stack: source volume imageIds unavailable; skipping');
        return false;
      }
      const kByImageId = new Map<string, number>();
      for (let k = 0; k < srcVolImageIds.length; k++) {
        kByImageId.set(srcVolImageIds[k], k);
      }

      const [nx, ny, nz] = labelmapVol.dimensions;
      const sliceLen = nx * ny;
      const arr = labelmapVol.voxelManager.getCompleteScalarDataArray();

      // Per-object model: this segmentation's stack labelmap and its MPR volume are the SAME single
      // binary object (values 0/1), 1:1 by geometry. Copy each volume slice verbatim into the stack
      // image at the matching source-slice index. No demux, no merge — overlap is handled by having
      // one segmentation (and one volume actor) PER object, not by packing values into one volume.
      let written = 0;
      for (const stackImageId of stackImageIds) {
        const segImg: any = cache.getImage(stackImageId);
        const refImageId: string | undefined = segImg?.referencedImageId;
        const k = refImageId != null ? kByImageId.get(refImageId) : undefined;
        if (k == null || k < 0 || k >= nz) {
          continue;
        }
        const sd = (segImg.voxelManager as csTypes.IVoxelManager<number>)?.getScalarData?.();
        if (!sd || sd.length !== sliceLen) {
          continue;
        }
        (sd as any).set((arr as any).subarray(k * sliceLen, (k + 1) * sliceLen));
        segImg.voxelManager?.setScalarData?.(sd);
        written++;
      }
      console.info(`[nninter] synced MPR volume→stack labelmap ${segmentationId}: ${written}/${stackImageIds.length} slices`);
      return written > 0;
    } catch (error) {
      console.warn('[nninter] sync volume→stack labelmap failed; export uses the stack labelmap as-is:', error);
      return false;
    }
  };

  const getMeasurementDataValues = (measurement: any): any[] => {
    return Object.values(measurement?.data ?? {});
  };

  const getActiveCornerstoneViewport = () => {
    const { activeViewportId } = viewportGridService.getState();
    return cornerstoneViewportService.getCornerstoneViewport(activeViewportId);
  };

  const measurementHasPromptPayload = (measurement: any): boolean => {
    const values = getMeasurementDataValues(measurement);
    const activeViewport = getActiveCornerstoneViewport();

    switch (measurement?.toolName) {
      case 'Probe2':
        return values.some((value: any) => value?.index?.length === 3) ||
          !!getPromptPointIJK(measurement, activeViewport);
      case 'RectangleROI2':
        return values.some((value: any) => value?.pointsInShape?.length) ||
          !!getRectangleBoxIJK(measurement, activeViewport);
      case 'PlanarFreehandROI3':
        return values.some((value: any) => value?.boundary?.length) ||
          !!getClosedFreehandBoundaryIJK(measurement, activeViewport);
      case 'PlanarFreehandROI2':
        return values.some((value: any) => value?.scribble?.length) ||
          !!getOpenFreehandIJK(measurement, activeViewport);
      default:
        return true;
    }
  };

  const runLiveNninter = () => {
    if (toolboxState.getLocked() || !toolboxState.getLiveMode()) {
      return;
    }

    // Live mode fires nninter() speculatively as the user draws. A transient failure
    // (e.g. an empty prompt that the backend answers with a zero-length seg part, which
    // surfaces as "seg part not found") must NOT propagate to the route error boundary
    // and crash the viewer. Swallow and log — the next complete measurement fires again.
    Promise.resolve(commandsManager.run('nninter')).catch(error => {
      console.warn('Live nninter() attempt failed (non-fatal):', error?.message || error);
    });
  };

  const waitForPromptPayloadAndRun = (measurementUID: string) => {
    if (!measurementUID || pendingLivePrompts.has(measurementUID)) {
      return;
    }

    let framesWaited = 0;
    // Freehand/lasso prompt payloads populate asynchronously over several frames; give
    // them ample time so a slow draw is caught by the wait loop (tryRun) rather than
    // timing out into a spurious empty fire.
    const maxFrames = 60;

    const cleanup = () => {
      const pending = pendingLivePrompts.get(measurementUID);
      if (pending?.unsubscribe) {
        pending.unsubscribe();
      }
      if (pending?.rafId != null) {
        cancelAnimationFrame(pending.rafId);
      }
      pendingLivePrompts.delete(measurementUID);
    };

    const tryRun = (measurement?: any): boolean => {
      const currentMeasurement = measurement ?? measurementService.getMeasurement(measurementUID);
      if (!currentMeasurement) {
        cleanup();
        return true;
      }

      if (measurementHasPromptPayload(currentMeasurement)) {
        cleanup();
        runLiveNninter();
        return true;
      }

      return false;
    };

    const subscription = measurementService.subscribe(
      measurementService.EVENTS.MEASUREMENT_UPDATED,
      ({ measurement }) => {
        if (measurement?.uid !== measurementUID) {
          return;
        }
        tryRun(measurement);
      }
    );

    const waitFrame = () => {
      if (tryRun()) {
        return;
      }

      framesWaited += 1;
      if (framesWaited >= maxFrames) {
        // Payload never populated (e.g. an abandoned/incomplete freehand draw). Do NOT
        // fire with an empty prompt: the backend returns a zero-length seg part that
        // surfaces as a fatal "seg part not found". A completed measurement fires nninter()
        // via the MEASUREMENT_ADDED / MEASUREMENT_UPDATED (tryRun) paths instead.
        console.debug('Prompt payload not populated after render frames; skipping live nninter().');
        cleanup();
        return;
      }

      const pending = pendingLivePrompts.get(measurementUID);
      if (pending) {
        pending.rafId = requestAnimationFrame(waitFrame);
      }
    };

    pendingLivePrompts.set(measurementUID, {
      unsubscribe: () => subscription.unsubscribe(),
      rafId: requestAnimationFrame(waitFrame),
    });
  };

  // Listen for measurement added events to trigger nninter() when live mode is enabled
  measurementService.subscribe(
    measurementService.EVENTS.MEASUREMENT_ADDED,
    (evt) => {
      if (toolboxState.getLiveMode() &&
      !toolboxState.getManualCorrectionMode() &&
      !evt.measurement?.metadata?.manualCorrection &&
      aiPromptToolNames.includes(
        evt.measurement.toolName
      )) {
        console.log('Live mode enabled, triggering nninter() for new measurement');
        if (!measurementHasPromptPayload(evt.measurement)) {
          waitForPromptPayloadAndRun(evt.measurement.uid);
          return;
        }

        runLiveNninter();
      }
    }
  );

  // Track which labelmap is authoritative during MANUAL CORRECTION so MPR brush edits persist.
  // A brush stroke fires SEGMENTATION_DATA_MODIFIED: if the active viewport is a volume/MPR pane the
  // edit landed in the VOLUME labelmap (mark it dirty → sync to the stack labelmap before export); if
  // it's the stack pane the stack labelmap was edited directly (it stays authoritative → clear dirty).
  // Gated on manual-correction mode so it ignores the events our own inference path dispatches.
  eventTarget.addEventListener(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, (evt: any) => {
    if (!toolboxState.getManualCorrectionMode()) {
      return;
    }
    const segId = evt?.detail?.segmentationId;
    if (!segId) {
      return;
    }
    if (getActiveCornerstoneViewport() instanceof BaseVolumeViewport) {
      // MPR brush edited this object's volume — mark it for verbatim sync back to its stack labelmap.
      _mprDirtySegIds.add(segId);
    } else {
      // Stack pane edited the stack labelmap directly — it stays authoritative.
      _mprDirtySegIds.delete(segId);
    }
  });

  // ── Layout-switch guard ────────────────────────────────────────────────────────────────────────
  // If a segmentation was created in a STACK-only layout it has imageIds but NO volumeId. When the user
  // switches to an MPR layout, OHIF re-adds that hydrated rep to the new volume panes and runs its own
  // (broken) stack→volume conversion → null scalars → vtkVolumeFS shader crash ("i is null"). The
  // crashing render is deferred to the next animation frame, so this handler — which fires synchronously
  // when the MPR volume loads — builds a proper volume labelmap, sets volumeId, and replaces the rep
  // BEFORE that render. Idempotent: a no-op once volumeId is set (normal MPR/refine, and 2nd+ events).
  // VolumeViewport3D panes are actively cleared because labelmap→surface conversion is unsafe here.
  let _mprGuardPromise: Promise<void> | undefined;
  let _mprGuardQueued = false;

  const ensureMprLabelmapForActiveSegmentations = async () => {
    try {
      const cvs = servicesManager.services.cornerstoneViewportService;
      const segSvc = servicesManager.services.segmentationService;
      const viewportIds: string[] = cvs.getViewportIds?.() ?? [];
      const mprVolumeViewportIds = viewportIds.filter(id => {
        const vp = cvs.getCornerstoneViewport(id);
        return vp instanceof BaseVolumeViewport && !(vp instanceof VolumeViewport3D);
      });
      const volume3DViewportIds = viewportIds.filter(id => {
        const vp = cvs.getCornerstoneViewport(id);
        return vp instanceof VolumeViewport3D;
      });
      if (!mprVolumeViewportIds.length && !volume3DViewportIds.length) {
        return;
      }
      const segmentations = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];

      if (volume3DViewportIds.length) {
        for (const seg of segmentations) {
          const lm: any = seg?.representationData?.[LABELMAP];
          if (!lm?.imageIds?.length) {
            continue;
          }
          for (const vpId of volume3DViewportIds) {
            try {
              await Promise.resolve(
                segSvc.removeSegmentationRepresentations(vpId, {
                  segmentationId: seg.segmentationId,
                })
              );
            } catch (error) {
              console.warn(`[nninter] 3D segmentation removal failed for ${vpId}:`, error);
            }
          }
        }
      }
      if (!mprVolumeViewportIds.length) {
        return;
      }
      // Quietly bail until at least one MPR pane actually has a source (non-labelmap) volume loaded.
      const anyVolumeReady = mprVolumeViewportIds.some(id => {
        const vp: any = cvs.getCornerstoneViewport(id);
        const ids: string[] = vp?.getAllVolumeIds?.() ?? (vp?.getVolumeId?.() ? [vp.getVolumeId()] : []);
        return ids.some(v => v && !v.endsWith('-mpr-labelmap'));
      });
      if (!anyVolumeReady) {
        return;
      }

      // Per-object model: ensure sibling (inactive) objects render in the MPR panes too.
      enableRenderInactiveSegmentations(mprVolumeViewportIds);

      for (const seg of segmentations) {
        if (_splitConsumedIds.has(seg.segmentationId)) {
          continue; // hidden split original — never rebuild/render its merged multi-value volume
        }
        const lm: any = seg?.representationData?.[LABELMAP];
        if (!lm?.imageIds?.length) {
          continue;
        }
        const sourceImageIds: string[] = lm.referencedImageIds ?? [];
        if (!sourceImageIds.length) {
          continue;
        }

        const expectedVolumeId = mprLabelmapVolumeId(seg.segmentationId);
        const hadVolumeId = lm.volumeId === expectedVolumeId;
        const segmentIndex = 1;
        const segmentColor = getObjectSegmentColor(seg, segmentIndex);
        if (!hadVolumeId) {
          const ok = await buildAndSyncLabelmapVolumeFor(
            seg.segmentationId,
            lm.imageIds,
            sourceImageIds,
            mprVolumeViewportIds
          );
          if (!ok) {
            continue;
          }
        }

        // Replace stack-style reps OHIF may have auto-added before volumeId existed. For segmentations
        // that were already volume-ready, only add the representation if this MPR viewport is missing it.
        for (const vpId of mprVolumeViewportIds) {
          try {
            const reps =
              segSvc.getSegmentationRepresentations?.(vpId, { segmentationId: seg.segmentationId }) ??
              [];
            const hasRep = reps.some((rep: any) => rep?.segmentationId === seg.segmentationId);
            if (hadVolumeId && hasRep) {
              setObjectSegmentColor(seg.segmentationId, segmentIndex, segmentColor, [vpId]);
              continue;
            }

            if (!hadVolumeId && hasRep) {
              await Promise.resolve(
                segSvc.removeSegmentationRepresentations(vpId, {
                  segmentationId: seg.segmentationId,
                })
              );
            }

            const afterRemove =
              segSvc.getSegmentationRepresentations?.(vpId, { segmentationId: seg.segmentationId }) ??
              [];
            const stillHasRep = afterRemove.some(
              (rep: any) => rep?.segmentationId === seg.segmentationId
            );
            if (!stillHasRep) {
              await segSvc.addSegmentationRepresentation(vpId, {
                segmentationId: seg.segmentationId,
              });
            }
            setObjectSegmentColor(seg.segmentationId, segmentIndex, segmentColor, [vpId]);
          } catch (e) {
            console.warn(`[nninter] MPR re-add on layout switch failed for ${vpId}:`, e);
          }
        }
        eventTarget.dispatchEvent(
          new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
            detail: { segmentationId: seg.segmentationId },
          })
        );
        console.info(`[nninter] layout switch: built MPR volume labelmap + re-added rep for ${seg.segmentationId}`);
      }
    } catch (error) {
      console.warn('[nninter] ensureMprLabelmapForActiveSegmentations failed:', error);
    }
  };

  // Subscribe to whichever viewport/grid events exist on this OHIF build (constants guarded so a name
  // mismatch degrades to "not subscribed" rather than throwing). The handler is idempotent, so multiple
  // overlapping triggers are harmless.
  const _runMprGuard = () => {
    if (_mprGuardPromise) {
      _mprGuardQueued = true;
      return;
    }

    _mprGuardPromise = ensureMprLabelmapForActiveSegmentations().finally(() => {
      _mprGuardPromise = undefined;
      if (_mprGuardQueued) {
        _mprGuardQueued = false;
        setTimeout(_runMprGuard, 0);
      }
    });
  };
  try {
    const cvsEvents: any = (cornerstoneViewportService as any).EVENTS || {};
    [cvsEvents.VIEWPORT_VOLUMES_CHANGED, cvsEvents.VIEWPORT_DATA_CHANGED]
      .filter(Boolean)
      .forEach(evtName => cornerstoneViewportService.subscribe(evtName, _runMprGuard));
  } catch (error) {
    console.warn('[nninter] could not subscribe to cornerstoneViewportService events for MPR guard:', error);
  }
  try {
    const gridEvents: any = (viewportGridService as any).EVENTS || {};
    [gridEvents.GRID_STATE_CHANGED, gridEvents.GRID_SIZE_CHANGED, gridEvents.LAYOUT_CHANGED]
      .filter(Boolean)
      .forEach(evtName => viewportGridService.subscribe(evtName, _runMprGuard));
  } catch (error) {
    console.warn('[nninter] could not subscribe to viewportGridService events for MPR guard:', error);
  }

  // ── Diagnostic logging ───────────────────────────────────────────────────────────────────────
  // Greppable logging so a real user workflow reveals runtime behavior we can't verify statically.
  // The BIG unknown: how OHIF hydrates an OVERLAPPING DICOM SEG on IMPORT — as ONE segmentation with
  // many segments (would break the 1-object-per-segmentation refine model + lose overlap), or as MANY
  // segmentations with one segment each (matches our authoring model → round-trip works). Grep console
  // for "[nninter/dbg]".
  const _segSummary = (seg: any): string => {
    if (!seg) return 'null';
    const lm: any = seg.representationData?.[LABELMAP] || {};
    const segIdx = Object.keys(seg.segments ?? {});
    let refSeries: string | undefined;
    try { refSeries = segSeriesUID(seg); } catch { /* ignore */ }
    return `id=${seg.segmentationId} label=${JSON.stringify(seg.label)} segments=[${segIdx.join(',')}] ` +
      `stackImgs=${lm.imageIds?.length ?? 0} volumeId=${lm.volumeId ? 'yes' : 'no'} ` +
      `refImgs=${(lm.referencedImageIds ?? []).length} refSeries=${refSeries ?? '?'}`;
  };
  const dumpSegmentations = (tag: string) => {
    try {
      const segs = (csToolsSegmentation.state.getSegmentations?.() ?? []) as any[];
      const totalSegments = segs.reduce((n, s) => n + Object.keys(s.segments ?? {}).length, 0);
      console.log(`[nninter/dbg] ${tag}: ${segs.length} segmentation(s), ${totalSegments} segment(s) total`);
      segs.forEach((s, i) => console.log(`[nninter/dbg]   [${i}] ${_segSummary(s)}`));
    } catch (e) {
      console.warn(`[nninter/dbg] dumpSegmentations(${tag}) failed:`, e);
    }
  };
  // Reveal how a multi-segment (imported) labelmap lays out its per-slice images: for a SAMPLE of
  // imageIds, print which source slice each references and the distinct nonzero values it holds. This
  // shows whether segments are stored as contiguous blocks ([seg1 slices..., seg2 slices...]) and what
  // pixel value each block uses — the info needed to write refinements into the CORRECT block.
  const dumpLabelmapLayout = (seg: any) => {
    try {
      const lm: any = seg?.representationData?.[LABELMAP] || {};
      const imageIds: string[] = lm.imageIds ?? [];
      const refIds: string[] = lm.referencedImageIds ?? [];
      if (!imageIds.length) {
        return;
      }
      const refIndex = new Map<string, number>();
      refIds.forEach((id, i) => refIndex.set(id, i));
      const n = imageIds.length;
      // Sample around the start, the suspected block boundaries (multiples of refIds.length), and end.
      const idxs = new Set<number>();
      const add = (i: number) => { if (i >= 0 && i < n) idxs.add(i); };
      [0, 1, 2].forEach(add);
      if (refIds.length) {
        for (let b = refIds.length; b < n; b += refIds.length) { add(b - 1); add(b); add(b + 1); }
      }
      [n - 3, n - 2, n - 1].forEach(add);
      const sorted = Array.from(idxs).sort((a, b) => a - b);
      console.log(`[nninter/dbg] layout ${seg.segmentationId}: imageIds=${n} refIds=${refIds.length} segments=[${Object.keys(seg.segments ?? {}).join(',')}]`);
      for (const i of sorted) {
        const img: any = cache.getImage(imageIds[i]);
        const rid: string | undefined = img?.referencedImageId;
        const ri = rid != null && refIndex.has(rid) ? refIndex.get(rid) : '?';
        let vals = 'uncached';
        const sd = img?.voxelManager?.getScalarData?.();
        if (sd) {
          const s = new Set<number>();
          for (let j = 0; j < sd.length; j++) { const v = sd[j]; if (v) { s.add(v); if (s.size > 4) break; } }
          vals = s.size ? Array.from(s).join('|') : '∅';
        }
        console.log(`[nninter/dbg]   img#${i} -> refSlice#${ri} nonzeroValues=${vals}`);
      }
    } catch (e) {
      console.warn('[nninter/dbg] dumpLabelmapLayout failed:', e);
    }
  };
  // ── Import-split ────────────────────────────────────────────────────────────────────────────
  // OHIF hydrates a DICOM SEG as ONE segmentation: overlapping SEG → N×S block imageIds (block r
  // holds value = segment index sortedIndices[r]); non-overlapping → one S-image labelmap with
  // values 1..N. The per-object model wants each object as its OWN segmentation (single map, value
  // 1). This splits a freshly-hydrated multi-object segmentation into N per-object segmentations,
  // preserving each segment's label + color, then removes the original. Idempotent + re-entrancy
  // guarded (the segmentations it creates fire SEGMENTATION_ADDED too).
  const _splitInProgress = new Set<string>();
  const _splitRetries = new Map<string, number>();

  /** Strip a segmentation's representations from every viewport — its STATE stays (OHIF's
   *  presentation store / SEG-displaySet link / toolbar evaluators reference it; deleting the state
   *  crashed the viewer with dangling-reference TypeErrors). */
  const _removeSegmentationRepsEverywhere = (segId: string) => {
    for (const vpId of cornerstoneViewportService.getViewportIds()) {
      try { segmentationService.removeSegmentationRepresentations(vpId, { segmentationId: segId }); } catch (e) { /* ignore */ }
    }
  };

  const _scheduleSplitRetry = (segmentationId: string, why: string) => {
    const n = (_splitRetries.get(segmentationId) ?? 0) + 1;
    _splitRetries.set(segmentationId, n);
    if (n <= 15) {
      setTimeout(() => {
        maybeSplitHydratedSegmentation(segmentationId).catch(e => console.warn('[nninter] split retry failed:', e));
      }, 300);
    } else {
      console.warn(`[nninter] import-split: giving up on ${segmentationId} (${why}); original left untouched`);
    }
  };

  const maybeSplitHydratedSegmentation = async (segmentationId: string) => {
    if (!segmentationId || _nninterManagedSegIds.has(segmentationId) || _splitInProgress.has(segmentationId)) {
      return;
    }
    // Already-split guard: the original's state is kept (hidden), so a later re-add of its
    // representations (viewport remount, re-hydration of the same SEG) just gets re-stripped —
    // never split twice (duplicate objects).
    if (_splitConsumedIds.has(segmentationId)) {
      _removeSegmentationRepsEverywhere(segmentationId);
      return;
    }
    const seg: any = csToolsSegmentation.state.getSegmentation(segmentationId);
    const lm: any = seg?.representationData?.[LABELMAP];
    const ids: string[] = lm?.imageIds ?? [];
    const segIndices = Object.keys(seg?.segments ?? {}).map(Number).filter(n => n > 0).sort((a, b) => a - b);
    if (!ids.length) {
      return; // volume-only or not-yet-populated — nothing to split
    }
    if (segIndices.length <= 1) {
      // Already per-object — adopt. If the single segment's index is k ≠ 1 (legal but rare), first
      // normalize it to the model's invariant (values 1, segments {1}) so activation, brush value,
      // and the AI refine path all line up.
      const k = segIndices[0];
      if (segIndices.length === 1 && k !== 1) {
        if (ids.some(id => !cache.getImage(id))) {
          _scheduleSplitRetry(segmentationId, 'normalize: labelmap images not cached yet');
          return;
        }
        try {
          for (const id of ids) {
            const sd = (cache.getImage(id) as any)?.voxelManager?.getScalarData?.();
            if (sd) for (let j = 0; j < sd.length; j++) sd[j] = sd[j] === k ? 1 : 0;
          }
          csToolsSegmentation.updateSegmentations([
            { segmentationId, payload: { segments: { 1: { ...(seg.segments[k] ?? {}), segmentIndex: 1 } } } },
          ]);
          eventTarget.dispatchEvent(new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, { detail: { segmentationId } }));
          console.log(`[nninter] import-split: normalized single-segment ${segmentationId} (index ${k} → 1)`);
        } catch (e) {
          console.warn(`[nninter] import-split: could not normalize ${segmentationId} (index ${k}); adopting as-is:`, e);
        }
      }
      _nninterManagedSegIds.add(segmentationId);
      _splitRetries.delete(segmentationId);
      return;
    }
    // Wait until hydration has cached all labelmap images (bounded retry).
    if (ids.some(id => !cache.getImage(id))) {
      _scheduleSplitRetry(segmentationId, 'labelmap images not cached yet');
      return;
    }
    // Wait until the viewport layer exists — splitting during viewport mount (hydration runs inside
    // it) mutates OHIF state mid-flow and crashed the viewer (toolbar/presentation-store TypeErrors).
    if (!cornerstoneViewportService.getViewportIds().length) {
      _scheduleSplitRetry(segmentationId, 'no viewports ready');
      return;
    }
    _splitInProgress.add(segmentationId);
    try {
      const refIds: string[] = lm.referencedImageIds?.length ? lm.referencedImageIds : segReferencedImageIds(seg);
      if (!refIds.length) {
        console.warn(`[nninter] import-split: no referenced imageIds for ${segmentationId}; skipping split (original kept)`);
        return;
      }
      const S = refIds.length;
      const seriesUID = segSeriesUID(seg);
      console.log(`[nninter] import-split: ${segmentationId} → ${segIndices.length} objects (imgs=${ids.length}, S=${S})`);

      // Classify viewports once (same rule as postSegmentationProcessing).
      const currentViewportIds = cornerstoneViewportService.getViewportIds();
      const stackViewportIds: string[] = [];
      const mprVolumeViewportIds: string[] = [];
      for (const viewportId of currentViewportIds) {
        const vp = cornerstoneViewportService.getCornerstoneViewport(viewportId);
        if (vp instanceof VolumeViewport3D) continue;
        else if (vp instanceof BaseVolumeViewport) mprVolumeViewportIds.push(viewportId);
        else stackViewportIds.push(viewportId);
      }

      // ── Phase 1: build all per-object segmentations (fresh images + state), counting voxels ──
      // LAYOUT-AGNOSTIC copy: OHIF's hydration layout varies — one shared block for non-overlapping
      // segments, separate blocks only where segments overlap (observed: 4 segments → 3×S imageIds).
      // So never index by block; instead make ONE pass over ALL original images, route each voxel by
      // its VALUE to that segment's object, and map the image to its output slice via
      // referencedImageId. Several source images can hit the same slice (one per block) — OR-merge.
      // Fresh derived images per object (never reuse the original's images — its reps get stripped
      // and OHIF may purge them from cache later).
      const zByRefId = new Map<string, number>();
      refIds.forEach((rid: string, z: number) => zByRefId.set(rid, z));
      const derivedByIndex = new Map<number, any[]>();
      for (const k of segIndices) {
        derivedByIndex.set(k, await imageLoader.createAndCacheDerivedLabelmapImages(refIds));
      }
      let totalCopied = 0;
      for (let i = 0; i < ids.length; i++) {
        const img: any = cache.getImage(ids[i]);
        const src = img?.voxelManager?.getScalarData?.();
        if (!src) continue;
        const z = zByRefId.get(img.referencedImageId) ?? (S > 0 ? i % S : i);
        for (let j = 0; j < src.length; j++) {
          const v = src[j];
          if (v > 0) {
            const dst = (derivedByIndex.get(v)?.[z] as any)?.voxelManager?.getScalarData?.();
            if (dst && j < dst.length) { dst[j] = 1; totalCopied++; }
          }
        }
      }

      // Data-loss guard: a multi-segment SEG that yields ZERO voxels means hydration hasn't written
      // the pixel data yet (images exist but are still blank). Nothing was created yet — leave the
      // original untouched and retry.
      if (totalCopied === 0) {
        _splitInProgress.delete(segmentationId);
        _scheduleSplitRetry(segmentationId, 'all objects empty — hydration data not ready?');
        return;
      }

      const newIds: string[] = [];
      const colorById = new Map<string, number[]>();
      const imageIdsById = new Map<string, string[]>();
      for (let r = 0; r < segIndices.length; r++) {
        const k = segIndices[r];
        const srcSegment: any = seg.segments[k];
        const objImageIds: string[] = (derivedByIndex.get(k) ?? []).map((im: any) => im.imageId);
        const newId = `${csUtils.uuidv4()}`;
        _nninterManagedSegIds.add(newId);
        newIds.push(newId);
        const color = (srcSegment?.color as number[]) || (srcSegment?.cachedStats?.color as number[]) || objectColorForOrdinal(r + 1);
        const label = srcSegment?.label || `Object ${r + 1}`;
        colorById.set(newId, color);
        imageIdsById.set(newId, objImageIds);
        csToolsSegmentation.addSegmentations([
          {
            segmentationId: newId,
            representation: { type: LABELMAP, data: { imageIds: objImageIds, referencedImageIds: refIds } },
            config: {
              cachedStats: { seriesInstanceUid: seriesUID },
              label,
              segments: {
                1: { segmentIndex: 1, label, color, locked: false, active: false, cachedStats: { color } },
              },
            },
          } as any,
        ]);
        rememberObjectSegmentation(seriesUID, newId);
      }

      // ── Phase 2: representations (stack first, then MPR volume) — mirror postSegmentationProcessing ──
      for (const newId of newIds) {
        const color = colorById.get(newId);
        const objImageIds = imageIdsById.get(newId) ?? [];
        await Promise.all(stackViewportIds.map(vpId =>
          segmentationService.addSegmentationRepresentation(vpId, { segmentationId: newId })
        ));
        setObjectSegmentColor(newId, 1, color, stackViewportIds);
        const volumeReady = await buildAndSyncLabelmapVolumeFor(newId, objImageIds, refIds, mprVolumeViewportIds);
        if (volumeReady) {
          await Promise.all(mprVolumeViewportIds.map(vpId =>
            segmentationService.addSegmentationRepresentation(vpId, { segmentationId: newId })
              .catch((error: any) => console.warn(`[nninter] import-split MPR add failed for ${vpId}:`, error))
          ));
          setObjectSegmentColor(newId, 1, color, mprVolumeViewportIds);
        }
      }
      enableRenderInactiveSegmentations(currentViewportIds);

      // Hide the original: strip its representations everywhere but KEEP its state — OHIF's
      // presentation store / SEG-displaySet link / toolbar evaluators still reference it (deleting
      // the state crashed the viewer). _splitConsumedIds excludes it from discovery, export, the
      // MPR guard, and re-splitting; a later rep re-add is re-stripped by the top guard.
      _splitConsumedIds.add(segmentationId);
      _removeSegmentationRepsEverywhere(segmentationId);

      for (const newId of newIds) {
        eventTarget.dispatchEvent(new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, { detail: { segmentationId: newId } }));
      }
      // Make the first object active so the user's next prompt REFINES it instead of silently
      // creating a new object (the hidden original may have been the active segmentation).
      if (newIds.length) {
        try { await commandsManager.run('setActiveSegmentation', { segmentationId: newIds[0] }); } catch (e) { /* ignore */ }
        try { segmentationService.setActiveSegment(newIds[0], 1); } catch (e) { /* ignore */ }
      }
      _splitRetries.delete(segmentationId);
      console.log(`[nninter] import-split done: ${segmentationId} → [${newIds.join(', ')}] (${totalCopied} voxels)`);
    } catch (error) {
      console.warn(`[nninter] import-split failed for ${segmentationId}:`, error);
    } finally {
      _splitInProgress.delete(segmentationId);
    }
  };

  // Observe segmentation lifecycle from BOTH layers (OHIF service + cs-tools eventTarget) so we catch
  // an import regardless of which one fires it. ADDED/REMOVED only — MODIFIED is far too chatty.
  try {
    const segEvents: any = (segmentationService as any).EVENTS || {};
    ['SEGMENTATION_ADDED', 'SEGMENTATION_REMOVED'].forEach(name => {
      const evtName = segEvents[name];
      if (!evtName) return;
      segmentationService.subscribe(evtName, (payload: any) => {
        const id = payload?.segmentationId ?? payload?.segmentation?.segmentationId ?? '?';
        console.log(`[nninter/dbg] svc ${name}: segmentationId=${id}`);
        dumpSegmentations(`after svc ${name}`);
        if (name === 'SEGMENTATION_ADDED' && id && id !== '?') {
          // Defer OUT of the hydration/viewport-mount call stack — SEGMENTATION_ADDED fires
          // synchronously inside createSegmentationForSEGDisplaySet, and mutating segmentation
          // state mid-flow crashed the viewer (toolbar/presentation-store dangling references).
          setTimeout(() => {
            maybeSplitHydratedSegmentation(id).catch(e => console.warn('[nninter] import-split error:', e));
          }, 250);
        }
      });
    });
  } catch (e) {
    console.warn('[nninter/dbg] could not subscribe to segmentationService lifecycle events:', e);
  }
  try {
    const E: any = (csToolsEnums as any).Events || {};
    [E.SEGMENTATION_ADDED, E.SEGMENTATION_REMOVED].filter(Boolean).forEach((evtName: string) => {
      eventTarget.addEventListener(evtName, (evt: any) => {
        console.log(`[nninter/dbg] cstools ${evtName}: ${JSON.stringify(evt?.detail ?? {}).slice(0, 200)}`);
        dumpSegmentations(`after cstools ${evtName}`);
      });
    });
  } catch (e) {
    console.warn('[nninter/dbg] could not subscribe to cs-tools segmentation events:', e);
  }

  /**
   * Helper function to handle post-segmentation processing after segmentation data is created/updated.
   * This includes updating representations, handling viewports, and triggering events.
   */
  // nnInteractive builds an image/STACK labelmap (per-slice derived images). Stack viewports render
  // it natively. ORTHOGRAPHIC MPR viewports (plain VolumeViewport) need a VOLUME labelmap, so we
  // derive one from the SOURCE CT volume (createAndCacheDerivedLabelmapVolume), copy the stack
  // labelmap into it by GEOMETRY (each source slice's ImagePositionPatient → volume k), and set
  // representationData.Labelmap.volumeId. OHIF then treats it as isVolumeSegmentation and renders it
  // natively (skipping its own broken stack→volume conversion). VolumeViewport3D panes are SKIPPED:
  // OHIF auto-converts a labelmap rep there into a Surface (polySeg), which crashes on these synthetic
  // labelmaps. The stack labelmap remains the source of truth (DICOM-SEG export, refine, undo); the
  // volume labelmap is display-only and re-synced from the stack labelmap on every inference.
  //
  // Prompt→server coordinates for off-axial planes are computed in the extension's coordinate helpers
  // (worldToIJKForMeasurement + the getters above): for volume/MPR viewports they take the volume index
  // and convert the volume slice k → the source display-set (stack) slice index the proxy expects. The
  // patched Cornerstone tools' own `volumeId:` branches are NOT relied on (they depend on a global
  // `services` and silently fell back, sending raw volume k as z → mis-placed MPR segments).

  /**
   * Build (or reuse) the derived labelmap VOLUME for a segmentation from the source CT volume, copy the
   * per-slice STACK labelmap into it by geometry, and set representationData.Labelmap.volumeId so OHIF
   * renders it natively in MPR/volume panes. Reusable from inference (postSegmentationProcessing) and
   * from the layout-switch guard (ensureMprLabelmapForActiveSegmentations). Fully guarded; returns true
   * iff a renderable volume labelmap is ready (so the caller may add the volume representation).
   */
  const buildAndSyncLabelmapVolumeFor = async (
    segmentationId: string,
    derivedImageIds: string[],
    sourceImageIds: string[],
    mprVolumeViewportIds: string[]
  ): Promise<boolean> => {
    if (!mprVolumeViewportIds.length) {
      return false;
    }
    const labelmapVolumeId = `${segmentationId}-mpr-labelmap`;
    try {
      // Source CT volumeId from any MPR pane (all MPR panes share one source volume). Our labelmap
      // volumes are ALSO actors in the viewport, so exclude ANY *-mpr-labelmap id (with overlapping
      // objects there are several) — never derive a labelmap from a labelmap.
      const _isLabelmapVol = (id: string) => !id || id.endsWith('-mpr-labelmap');
      let refVolumeId: string | undefined;
      for (const vpId of mprVolumeViewportIds) {
        const vp = servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(vpId);
        const allIds: string[] = (vp as any)?.getAllVolumeIds?.() ?? [];
        let candidate = allIds.find(id => !_isLabelmapVol(id));
        if (!candidate) {
          const single = (vp as any)?.getVolumeId?.();
          candidate = single && !_isLabelmapVol(single) ? single : undefined;
        }
        if (candidate) {
          refVolumeId = candidate;
          break;
        }
      }
      if (!refVolumeId) {
        console.warn('[nninter] MPR: no source volumeId found on MPR viewports; skipping volume overlay');
        return false;
      }
      // Remember the source CT volume for the reverse (volume→stack) sync used by manual correction.
      _mprRefVolumeIdBySeg.set(segmentationId, refVolumeId);

      let vol: any = cache.getVolume(labelmapVolumeId);
      if (!vol) {
        vol = volumeLoader.createAndCacheDerivedLabelmapVolume(refVolumeId, { volumeId: labelmapVolumeId });
      }
      const vm = vol?.voxelManager;
      if (!vol || !vm?.getCompleteScalarDataArray || !vm?.setCompleteScalarDataArray) {
        console.warn('[nninter] MPR: derived labelmap volume unavailable or not image-backed; skipping');
        return false;
      }

      const [nx, ny, nz] = vol.dimensions;
      const sliceLen = nx * ny;
      const volImageData = vol.imageData;

      // Map each source slice → volume k using the SOURCE VOLUME's own imageId ordering, which IS the
      // authoritative geometric order Cornerstone placed slices in (IPP-projected). The derived labelmap
      // volume shares that geometry, so slice k of the source = slice k of the labelmap. Robust to the
      // high-priority imagePlaneModule provider (pixel spacing only); transformWorldToIndex is fallback.
      const srcVol: any = cache.getVolume(refVolumeId);
      const srcVolImageIds: string[] = srcVol?.imageIds ?? [];
      const kByImageId = new Map<string, number>();
      for (let k = 0; k < srcVolImageIds.length; k++) {
        kByImageId.set(srcVolImageIds[k], k);
      }

      // Read (copy), zero, then write each stack labelmap slice into its volume k.
      const arr = vm.getCompleteScalarDataArray();
      (arr as any).fill?.(0);

      let written = 0;
      let skipped = 0;
      let usedFallback = 0;
      const kSeen: number[] = [];
      for (let idx = 0; idx < derivedImageIds.length; idx++) {
        const derived = cache.getImage(derivedImageIds[idx]);
        if (!derived) { skipped++; continue; }
        // Segment model: imageIds is N per-segment BLOCKS, each block re-referencing the same source
        // slices. Map to the volume slice by the derived image's OWN referencedImageId (works for every
        // block) and only fall back to positional sourceImageIds[idx] for a 1:1 single-block labelmap.
        const srcImageId = (derived as any).referencedImageId ?? sourceImageIds[idx];
        if (!srcImageId) { skipped++; continue; }

        let k = kByImageId.has(srcImageId) ? (kByImageId.get(srcImageId) as number) : -1;
        if (k < 0) {
          // Fallback: derive k from the slice's ImagePositionPatient via the volume geometry.
          const plane: any = metaData.get('imagePlaneModule', srcImageId);
          const ipp = plane?.imagePositionPatient;
          if (ipp) {
            const kk = csUtils.transformWorldToIndex(volImageData, ipp)[2];
            if (Number.isFinite(kk)) { k = kk; usedFallback++; }
          }
        }
        if (k < 0 || k >= nz) { skipped++; continue; }

        const sd = (derived.voxelManager as csTypes.IVoxelManager<number>)?.getScalarData?.();
        if (!sd || sd.length !== sliceLen) { skipped++; continue; }
        // MERGE nonzero voxels (do NOT .set() the whole slice) so overlapping segment blocks sharing a
        // source slice don't erase one another. The volume is single-value, so a later block wins on
        // shared voxels — MPR overlap is best-effort; the stack view shows the true overlap.
        const base = k * sliceLen;
        for (let j = 0; j < sliceLen; j++) { if (sd[j] !== 0) (arr as any)[base + j] = sd[j]; }
        written++;
        if (kSeen.length < 3) kSeen.push(k);
      }
      vm.setCompleteScalarDataArray(arr);
      console.info(
        `[nninter] MPR labelmap volume ${labelmapVolumeId}: dims=${nx}x${ny}x${nz}, ` +
        `wrote ${written}/${derivedImageIds.length} slices (skipped ${skipped}, fallback ${usedFallback}); ` +
        `sample k=${kSeen.join(',')}`
      );

      // Attach volumeId to the segmentation's labelmap representation (preserve imageIds + other reps).
      const seg = csToolsSegmentation.state.getSegmentation(segmentationId);
      const repData: any = seg?.representationData || {};
      const lm: any = repData[LABELMAP] || {};
      if (lm.volumeId !== labelmapVolumeId) {
        csToolsSegmentation.updateSegmentations([
          {
            segmentationId,
            payload: {
              representationData: {
                ...repData,
                [LABELMAP]: { ...lm, volumeId: labelmapVolumeId },
              },
            },
          },
        ]);
      }
      // The volume was just rebuilt from the stack labelmap, so they match again — drop any pending
      // manual-correction dirty marker for this segmentation.
      _mprDirtySegIds.delete(segmentationId);
      return true;
    } catch (error) {
      console.warn('[nninter] MPR volume labelmap build/sync failed; MPR overlay skipped:', error);
      return false;
    }
  };

  async function postSegmentationProcessing({
    activeViewportId,
    segmentationId,
    segmentNumber,
    segments,
    derivedImageIds,
    currentDisplaySets,
    imageIds,
    existingSegments,
    existing,
    mode,
    activeSegmentation,
    currentImageIdIndex,
    z_range,
  }: {
    activeViewportId: string;
    segmentationId: string;
    segmentNumber: number;
    segments: { [segmentIndex: string]: cstTypes.Segment };
    derivedImageIds: string[];
    currentDisplaySets: any;
    imageIds: string[];
    existingSegments: { [segmentIndex: string]: cstTypes.Segment };
    existing: boolean;
    mode?: 'new-segmentation' | 'refine';
    activeSegmentation: any;
    currentImageIdIndex?: number;
    z_range: number[];
  }) {
    rememberObjectSegmentation(currentDisplaySets?.SeriesInstanceUID, segmentationId);
    _nninterManagedSegIds.add(segmentationId); // ours — the import-split must not re-split it

    // Get the representations for the segmentation to recover the visibility of the segments
    const representations = servicesManager.services.segmentationService.getSegmentationRepresentations(activeViewportId, { segmentationId });
    const segmentColor = getObjectSegmentColor({ segments }, segmentNumber);

    if (!existing) {
      // New object → its own segmentation (single segment, index 1). Tag it with the source series so
      // siblings can be discovered (overlapping export, MPR guard, refine resolution).
      csToolsSegmentation.addSegmentations([
        {
          segmentationId,
          representation: {
            type: LABELMAP,
            data: {
              imageIds: derivedImageIds,
              referencedVolumeId: currentDisplaySets.displaySetInstanceUID,
              referencedImageIds: imageIds,
            }
          },
          config: {
            cachedStats: {
              center: z_range.length > 0 ? z_range.reduce((sum, z) => sum + z, 0) / z_range.length : 0,
              seriesInstanceUid: currentDisplaySets.SeriesInstanceUID,
            },
            label: segments[segmentNumber]?.label ?? currentDisplaySets.SeriesDescription,
            segments,
          },
        }
      ]);
    } else {
      const readableText = customizationService.getCustomization('panelSegmentation.readableText');

      // Get existing segmentation to preserve other representation data
      const existingSegmentation = csToolsSegmentation.state.getSegmentation(segmentationId);
      const existingRepresentationData = existingSegmentation?.representationData || {};
      const existingLabelmapData = existingRepresentationData[LABELMAP] || {};

      // For Surface representation, remove it entirely to force regeneration from updated labelmap
      // This ensures surfaces are recomputed from the new labelmap data
      const updatedRepresentationData = { ...existingRepresentationData };
      const SURFACE = csToolsEnums.SegmentationRepresentations.Surface;
      if (updatedRepresentationData[SURFACE]) {
        // Remove Surface representation data to force regeneration from updated labelmap
        delete updatedRepresentationData[SURFACE];
      }

      // Update the segmentation data, preserving other representation data (but not Surface)
      csToolsSegmentation.updateSegmentations([
        {
          segmentationId,
          payload: {
            segments: segments,
            representationData: {
              ...updatedRepresentationData, // Surface data removed to force regeneration
              [LABELMAP]: {
                ...existingLabelmapData, // Preserve existing labelmap data (e.g., volumeId)
                imageIds: derivedImageIds,
                referencedVolumeId: currentDisplaySets.displaySetInstanceUID,
                referencedImageIds: imageIds,
              }
            }
          },
        },
      ]);

      // Update the segmentation stats
      Promise.resolve().then(() =>
        updateSegmentationStats({
          segmentation: activeSegmentation,
          segmentationId,
          readableText,
        })
      ).catch(error => {
        console.warn('Failed to update segmentation stats:', error);
      });
    }

    // Classify viewports. The nnInteractive labelmap is stack-based; stack viewports render the
    // per-slice images directly. Orthographic MPR viewports (plain VolumeViewport) get a derived
    // labelmap VOLUME built from the source CT (see buildAndSyncLabelmapVolume). VolumeViewport3D
    // panes are skipped — OHIF turns a labelmap rep there into a Surface (polySeg), which crashes.
    const currentViewportIds = servicesManager.services.cornerstoneViewportService.getViewportIds();
    const stackViewportIds: string[] = [];
    const mprVolumeViewportIds: string[] = [];
    const volume3DViewportIds: string[] = [];
    for (const viewportId of currentViewportIds) {
      const vp = servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(viewportId);
      if (vp instanceof VolumeViewport3D) volume3DViewportIds.push(viewportId);
      else if (vp instanceof BaseVolumeViewport) mprVolumeViewportIds.push(viewportId);
      else stackViewportIds.push(viewportId);
    }

    // Build/sync the derived labelmap VOLUME (delegates to the reusable closure-level helper, passing
    // this inference's local slice arrays). Returns true if a renderable volume labelmap is ready.
    const buildAndSyncLabelmapVolume = () =>
      buildAndSyncLabelmapVolumeFor(segmentationId, derivedImageIds, imageIds, mprVolumeViewportIds);

    if (!existing) {
      // ── New object: build the segmentation + representations so it renders. A refine (in-place
      // voxel edit of the same map) takes the fast path in the else. ──

      // Recover the visibility of any pre-existing segments
      for (let i = 0; i < representations.length; i++) {
        const representation = representations[i];
        const segs = Object.values(representation.segments);
        for (let j = 0; j < segs.length; j++) {
          const seg = segs[j];
          servicesManager.services.segmentationService.setSegmentVisibility(activeViewportId, representation.segmentationId, (seg as any).segmentIndex, (seg as any).visible);
        }
      }

      for (const viewportId of currentViewportIds) {
        servicesManager.services.segmentationService.removeSegmentationRepresentations(viewportId, { segmentationId });
      }
      // Add the STACK representation first, while representationData.Labelmap has NO volumeId, so
      // OHIF treats it as a stack segmentation for these viewports.
      await Promise.all(stackViewportIds.map(viewportId =>
        servicesManager.services.segmentationService.addSegmentationRepresentation(viewportId, { segmentationId })
      ));
      setObjectSegmentColor(segmentationId, segmentNumber, segmentColor, stackViewportIds);
      // Per-object model: each object is its OWN segmentation, so sibling objects are "inactive"
      // segmentations. They must still render (overlap) — force render-inactive on for every viewport.
      enableRenderInactiveSegmentations(currentViewportIds);
      // Then build the volume labelmap (sets volumeId) and add the representation to MPR panes, which
      // OHIF now renders natively (isVolumeSegmentation). Done AFTER the stack add so the stack path
      // is unaffected by the volumeId.
      const volumeReady = await buildAndSyncLabelmapVolume();
      if (volumeReady) {
        await Promise.all(mprVolumeViewportIds.map(viewportId =>
          servicesManager.services.segmentationService
            .addSegmentationRepresentation(viewportId, { segmentationId })
            .catch((error: any) => console.warn(`[nninter] MPR add representation failed for ${viewportId}:`, error))
        ));
        setObjectSegmentColor(segmentationId, segmentNumber, segmentColor, mprVolumeViewportIds);
      }
      if (volume3DViewportIds.length) {
        console.info('[nninter] 3D viewport(s) skipped — labelmap→surface generation disabled to avoid the polySeg crash');
      }

      // Scroll-away-back so Cornerstone creates the VTK actors for the current slice
      // and uploads the initial GPU texture (only needed on first-ever inference).
      const activeVp = activeViewportId.startsWith('default')
        ? servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(activeViewportId)
        : null;
      if (activeVp?.setImageIdIndex && currentImageIdIndex !== undefined) {
        const away = currentImageIdIndex === 0 ? 1 : 0;
        await activeVp.setImageIdIndex(away);
        await activeVp.setImageIdIndex(currentImageIdIndex);
      }

      eventTarget.dispatchEvent(
        new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
          detail: { segmentationId },
        })
      );
    } else {
      // ── Refinement / update (existing segment) — fast path ──
      // The stack labelmap images were updated in place by the voxel-writing loop. Re-sync the volume
      // labelmap from them so the MPR panes update too, then dispatch SEGMENTATION_DATA_MODIFIED to
      // re-upload the GPU texture for both stack and volume viewports on the next render.
      await buildAndSyncLabelmapVolume();
      eventTarget.dispatchEvent(
        new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
          detail: { segmentationId },
        })
      );
    }

    try {
      await commandsManager.run('setActiveSegmentation', { segmentationId });
    } catch (error) {
      console.warn(`[nninter] could not activate segmentation ${segmentationId}:`, error);
    }
    servicesManager.services.segmentationService.setActiveSegment(segmentationId, segmentNumber);
    toolboxState.setCurrentActiveSegment(segmentNumber);

    if (toolboxState.getRefineNew()) {
      toolboxState.setRefineNew(false);
    }
  }


  const actions = {
    async armNextNninterObject() {
      if (toolboxState.getLocked()) {
        return;
      }
      // Per-object model: "next object" just arms creation. The next prompt creates a fresh
      // segmentation (nninter, mode='new-segmentation') — no empty object created up front.
      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      const displaySetInstanceUID = activeViewportSpecificData?.displaySetInstanceUIDs?.[0];
      const currentDisplaySets = displaySetService.activeDisplaySets.find(
        e => e.displaySetInstanceUID === displaySetInstanceUID
      );
      if (!currentDisplaySets || currentDisplaySets.Modality === 'SEG') {
        uiNotificationService.show({
          title: 'nnInteractive',
          message: 'Select the source image viewport before creating the next object.',
          type: 'warning',
        });
        return;
      }

      toolboxState.setRefineNew(true);
      toolboxState.setPosNeg(false);
      const nextOrdinal = seriesSegmentations(currentDisplaySets.SeriesInstanceUID).length + 1;
      console.log(`[nninter/dbg] armNextNninterObject: armed new object ${nextOrdinal} (lazy — draw a prompt)`);
      uiNotificationService.show({
        title: 'nnInteractive',
        message: `Draw a prompt to create Object ${nextOrdinal}.`,
        type: 'info',
      });
    },

    runSegmentBidirectional: async ({ segmentationId, segmentIndex } = {}) => {
      const activeViewportId = viewportGridService.getActiveViewportId();
      const activeSegmentation = segmentationService.getActiveSegmentation(activeViewportId);
      const activeSegment = segmentationService.getActiveSegment(activeViewportId);
      const targetId = segmentationId || activeSegmentation?.segmentationId;
      const targetIndex = segmentIndex ?? activeSegment?.segmentIndex;

      if (!targetId || targetIndex == null) {
        return;
      }

      const bidirectionalData = await cornerstoneTools.utilities.segmentation.getSegmentLargestBidirectional({
        segmentationId: targetId,
        segmentIndices: [targetIndex],
      });

      let measurementVisibilityChanged = false;

      bidirectionalData.forEach(measurement => {
        const { segmentIndex, majorAxis, minorAxis, referencedImageId } = measurement;
        const annotation = cornerstoneTools.SegmentBidirectionalTool.hydrate(
          activeViewportId,
          [majorAxis, minorAxis],
          {
            segmentIndex,
            segmentationId: targetId,
            referencedImageId,
          }
        );

        measurement.annotationUID = annotation.annotationUID;

        const isVisible = cornerstoneTools.annotation.visibility.isAnnotationVisible(
          annotation.annotationUID
        );
        if (isVisible) {
          cornerstoneTools.annotation.visibility.setAnnotationVisibility(
            annotation.annotationUID,
            false
          );
          measurementVisibilityChanged = true;
        }

        const updatedSegmentation = updateSegmentBidirectionalStats({
          segmentationId: targetId,
          segmentIndex: targetIndex,
          bidirectionalData: measurement,
          segmentationService,
          annotation,
        });

        if (updatedSegmentation) {
          segmentationService.addOrUpdateSegmentation({
            segmentationId: targetId,
            segments: updatedSegmentation.segments,
          });
        }
      });

      if (measurementVisibilityChanged) {
        dispatchMeasurementStateChanged();
      }
    },

    updateStoredSegmentationPresentation: ({ displaySet, type }) => {
      const { addSegmentationPresentationItem, clearSegmentationPresentationStore } =
        useSegmentationPresentationStore.getState();

      clearSegmentationPresentationStore();
      commandsManager.run('clearMeasurements');

      const referencedDisplaySetInstanceUID = displaySet.referencedDisplaySetInstanceUID;
      addSegmentationPresentationItem(referencedDisplaySetInstanceUID, {
        segmentationId: displaySet.displaySetInstanceUID,
        hydrated: true,
        type,
      });
    },

    toggleToolActiveToolbar: ({ value, itemId, toolName, toolGroupIds = [] }) => {
      toolName = toolName || itemId || value;
      toolGroupIds = toolGroupIds.length ? toolGroupIds : toolGroupService.getToolGroupIds();

      const { activeViewportId } = viewportGridService.getState();
      const activeToolGroup = toolGroupService.getToolGroupForViewport(activeViewportId);
      const isCurrentlyActive = activeToolGroup?.getActivePrimaryMouseButtonTool() === toolName;

      if (isCurrentlyActive) {
        toolGroupIds.forEach(toolGroupId => {
          const tg = toolGroupService.getToolGroup(toolGroupId);
          if (tg?.hasTool(toolName)) {
            tg.setToolPassive(toolName);
          }
          if (tg?.hasTool('Pan')) {
            commandsManager.run('setToolActive', { toolName: 'Pan', toolGroupId });
          }
        });
        return;
      }

      commandsManager.run('setToolActiveToolbar', { value, itemId, toolName, toolGroupIds });
    },

    toggleSegmentMeasurement: ({ segmentationId, segmentIndex }) => {
      let measurementVisibilityChanged = false;

      measurementService
        .getMeasurements()
        .filter(
          measurement =>
            measurement?.metadata?.segmentationId === segmentationId &&
            measurement?.metadata?.SegmentNumber === segmentIndex
        )
        .forEach(measurement => {
          measurementService.toggleVisibilityMeasurement(measurement.uid, !measurement.isVisible);
          measurementVisibilityChanged = true;
        });

      if (measurementVisibilityChanged) {
        dispatchMeasurementStateChanged();
      }
    },

    getSegmentMeasurementVisibility: ({ segmentationId, segmentIndex }) => {
      const selectedMeasurements = measurementService
        .getMeasurements()
        .filter(
          measurement =>
            measurement?.metadata?.segmentationId === segmentationId &&
            measurement?.metadata?.SegmentNumber === segmentIndex
        );

      return selectedMeasurements.some(measurement => measurement.isVisible);
    },

    toggleSegmentationVisibilityAllViewports: ({ segmentationId, type }) => {
      const viewportIds = cornerstoneViewportService.getViewportIds();
      let targetSegmentationId = segmentationId;

      if (!targetSegmentationId) {
        const activeViewportId = viewportGridService.getActiveViewportId();
        const activeSegmentation = segmentationService.getActiveSegmentation(activeViewportId);
        if (!activeSegmentation) {
          console.warn('No active segmentation found');
          return;
        }
        targetSegmentationId = activeSegmentation.segmentationId;
      }

      const representationType = type || LABELMAP;
      viewportIds.forEach(viewportId => {
        segmentationService.toggleSegmentationRepresentationVisibility(viewportId, {
          segmentationId: targetSegmentationId,
          type: representationType,
        });
      });
    },

    removeSegmentationFromViewport: ({ segmentationId }) => {
      commandsManager.runCommand('resetNninter', { clearMeasurements: true });
      segmentationService.removeSegmentationRepresentations(viewportGridService.getActiveViewportId(), {
        segmentationId,
      });
    },

    async generateSegmentation({ segmentationId, options = {} }) {
      // Overlapping DICOM SEG export. Each nnInteractive object is its OWN segmentation, so gather all
      // sibling objects for this source series and emit ONE SEG whose segments MAY overlap: every object
      // becomes its own DICOM segment, and overlapping voxels are encoded as separate frames referencing
      // the same source frame (the adapter appends per-segment frames). Falls back to a single-object
      // export when siblings can't be discovered.
      const targetSeg =
        csToolsSegmentation.state.getSegmentation(segmentationId) ??
        segmentationService.getSegmentation(segmentationId);
      const { activeViewportId: exportActiveViewportId, viewports: exportViewports } = viewportGridService.getState();
      const exportViewportData = exportViewports.get(exportActiveViewportId);
      const exportDisplaySetInstanceUID = exportViewportData?.displaySetInstanceUIDs?.[0];
      const exportDisplaySet = displaySetService.activeDisplaySets.find(
        (displaySet: any) => displaySet.displaySetInstanceUID === exportDisplaySetInstanceUID
      );
      const activeSourceSeries =
        exportDisplaySet && exportDisplaySet.Modality !== 'SEG'
          ? exportDisplaySet.SeriesInstanceUID
          : undefined;
      const activeSourceImageIds: string[] =
        exportDisplaySet && exportDisplaySet.Modality !== 'SEG'
          ? (exportDisplaySet.imageIds ?? [])
          : [];
      const targetReferencedImageIds = segReferencedImageIds(targetSeg);
      const targetFirstInstance: any = targetReferencedImageIds[0]
        ? metaData.get('instance', targetReferencedImageIds[0])
        : undefined;
      const targetSeries =
        segSeriesUID(targetSeg) || targetFirstInstance?.SeriesInstanceUID || activeSourceSeries;
      const sourceImageIdsForDiscovery = targetReferencedImageIds.length
        ? targetReferencedImageIds
        : activeSourceImageIds;
      let siblings = targetSeries
        ? seriesSegmentations(targetSeries, sourceImageIdsForDiscovery)
        : allSegmentationStates().filter(seg =>
            sameReferencedImageStack(segReferencedImageIds(seg), sourceImageIdsForDiscovery)
          );
      if (targetSeg && !siblings.some((s: any) => s.segmentationId === segmentationId)) {
        siblings = [targetSeg, ...siblings];
      }
      if (!siblings.length) {
        throw new Error('No segmentation found to export');
      }
      dumpSegmentations('export: before build');
      console.log(
        `[nninter/dbg] export: target=${segmentationId} targetSeries=${targetSeries ?? '?'} ` +
        `siblings=${siblings.length} [${siblings.map((s: any) =>
          `${s.segmentationId}:${Object.keys(s.segments ?? {}).length}seg`).join(', ')}]`
      );

      // Fold any pending MPR (volume-labelmap) edits back into the stack labelmaps we read below.
      for (const sib of siblings) {
        if (_mprDirtySegIds.has(sib.segmentationId)) {
          syncVolumeLabelmapToStack(sib.segmentationId);
          _mprDirtySegIds.delete(sib.segmentationId);
        }
      }

      // Segment model: the series segmentation stores N segments as contiguous per-slice BLOCKS
      // (imageIds = N × sliceCount; block rank r = the r-th segment, value = its index). Expand each
      // real segmentation into one PSEUDO-segmentation per segment block so the per-object loop below
      // (which treats each unit as a single binary object → one DICOM segment) emits one segment/block.
      const _exportS = sourceImageIdsForDiscovery.length || activeSourceImageIds.length || 0;
      const expandToSegmentBlocks = (segs: any[]): any[] => {
        const units: any[] = [];
        for (const seg of segs) {
          const ids: string[] = (seg.representationData?.[LABELMAP] as any)?.imageIds ?? [];
          const refIds: string[] = segReferencedImageIds(seg);
          const indices = Object.keys(seg.segments ?? {}).map(Number).filter(n => n > 0).sort((a, b) => a - b);
          if (!ids.length || !indices.length) {
            continue;
          }
          const S = refIds.length || _exportS || Math.floor(ids.length / indices.length);
          const isMultiBlock = S > 0 && ids.length !== S && ids.length % S === 0 && ids.length / S === indices.length;
          if (isMultiBlock) {
            indices.forEach((k, rank) => {
              units.push({
                segmentationId: seg.segmentationId,
                representationData: { [LABELMAP]: { imageIds: ids.slice(rank * S, rank * S + S), referencedImageIds: refIds.slice(0, S) } },
                segments: seg.segments,
                // Block rank r belongs to segment k BY LAYOUT — carry it so the per-object loop
                // doesn't have to infer the segment from pixel values (stray foreign values in a
                // block would mislabel/miscolor the exported object).
                exportSegmentIndex: k,
              });
            });
          } else {
            // One segment (single block) or a non-block layout — emit the segmentation as one unit.
            units.push({
              segmentationId: seg.segmentationId,
              representationData: { [LABELMAP]: { imageIds: ids, referencedImageIds: refIds } },
              segments: seg.segments,
            });
          }
        }
        return units.length ? units : segs;
      };
      const exportUnits = expandToSegmentBlocks(siblings);
      console.log(`[nninter/dbg] export: expanded ${siblings.length} segmentation(s) → ${exportUnits.length} segment block(s)`);

      // Shared source images (all blocks reference the same series); built from the first block (S images).
      const sourceSibling =
        exportUnits.find((sib: any) => ((sib.representationData?.[LABELMAP] as any)?.imageIds ?? []).length) ??
        exportUnits[0];
      const firstImageIds: string[] = (sourceSibling.representationData?.[LABELMAP] as any)?.imageIds ?? [];
      const firstSegImages = firstImageIds.map((imageId: string) => cache.getImage(imageId));
      const referencedImageIds = firstSegImages.map((image: any) => image?.referencedImageId);
      await Promise.all(
        referencedImageIds.map((referencedImageId: string) => {
          if (!referencedImageId || cache.getImage(referencedImageId)) {
            return Promise.resolve();
          }
          return imageLoader.loadAndCacheImage(referencedImageId).catch(error => {
            console.warn(`Failed to load referenced image ${referencedImageId}:`, error);
          });
        })
      );
      const referencedImages = firstSegImages.map((image: any) =>
        image?.referencedImageId ? cache.getImage(image.referencedImageId) : null
      );
      const numFrames = referencedImages.length;

      // Build one binary labelmap3D per object. This is the DICOM-SEG overlapping representation:
      // each object is its own binary channel, and multiple channels may contain the same voxel.
      const refIndexByImageId = new Map<string, number>();
      referencedImageIds.forEach((imageId: string, index: number) => {
        if (imageId) {
          refIndexByImageId.set(imageId, index);
        }
      });
      const makeEmptyLabelmaps2D = () => firstSegImages.map((image: any) => {
        const rows = image?.rows;
        const columns = image?.columns;
        return {
          segmentsOnLabelmap: [] as number[],
          pixelData: new Uint8Array((rows ?? 0) * (columns ?? 0)),
          rows,
          columns,
        };
      });

      const asArray = (value: any): any[] => {
        if (!value) {
          return [];
        }
        return Array.isArray(value) ? value : [value];
      };

      const clonePlain = (value: any): any =>
        value == null ? value : JSON.parse(JSON.stringify(value));

      const pixelDataBytes = (pixelData: any): Uint8Array => {
        if (!pixelData) {
          return new Uint8Array(0);
        }
        if (pixelData instanceof Uint8Array) {
          return pixelData;
        }
        if (pixelData instanceof ArrayBuffer) {
          return new Uint8Array(pixelData);
        }
        if (ArrayBuffer.isView(pixelData)) {
          return new Uint8Array(pixelData.buffer, pixelData.byteOffset, pixelData.byteLength);
        }
        if (Array.isArray(pixelData)) {
          return new Uint8Array(pixelData);
        }
        return new Uint8Array(0);
      };

      const readBit = (bytes: Uint8Array, bitIndex: number): number =>
        (bytes[Math.floor(bitIndex / 8)] >> (bitIndex % 8)) & 1;

      const writeBit = (bytes: Uint8Array, bitIndex: number, value: number) => {
        if (!value) {
          return;
        }
        bytes[Math.floor(bitIndex / 8)] |= 1 << (bitIndex % 8);
      };

      const setFrameSegmentNumber = (frame: any, segmentNumber: number): any => {
        const frameCopy = clonePlain(frame);
        const segmentIdSequence = asArray(frameCopy.SegmentIdentificationSequence);
        if (segmentIdSequence[0]) {
          segmentIdSequence[0].ReferencedSegmentNumber = segmentNumber;
          frameCopy.SegmentIdentificationSequence = Array.isArray(frameCopy.SegmentIdentificationSequence)
            ? segmentIdSequence
            : segmentIdSequence[0];
        }

        const frameContentSequence = asArray(frameCopy.FrameContentSequence);
        if (frameContentSequence[0]?.DimensionIndexValues?.length) {
          frameContentSequence[0].DimensionIndexValues[0] = segmentNumber;
          frameCopy.FrameContentSequence = Array.isArray(frameCopy.FrameContentSequence)
            ? frameContentSequence
            : frameContentSequence[0];
        }
        return frameCopy;
      };

      const combineSingleObjectSegs = (singleObjectResults: any[]): any => {
        const firstDataset = singleObjectResults[0]?.dataset;
        if (!firstDataset) {
          throw new Error('No single-object SEG dataset available to combine');
        }

        const frameBitLength =
          Number(firstDataset.Rows ?? referencedImages[0]?.rows ?? 0) *
          Number(firstDataset.Columns ?? referencedImages[0]?.columns ?? 0);
        const combinedSegmentSequence: any[] = [];
        const combinedFrameSequence: any[] = [];
        let totalFrames = 0;

        for (const { dataset } of singleObjectResults) {
          totalFrames += Number(dataset.NumberOfFrames ?? asArray(dataset.PerFrameFunctionalGroupsSequence).length);
        }

        const combinedPixelDataLength = Math.ceil((frameBitLength * totalFrames) / 8);
        const combinedPixelData = new Uint8Array(
          combinedPixelDataLength + (combinedPixelDataLength % 2)
        );
        let frameOffset = 0;
        let segmentNumber = 1;

        for (const { dataset } of singleObjectResults) {
          const segment = clonePlain(asArray(dataset.SegmentSequence)[0]);
          if (!segment) {
            continue;
          }
          segment.SegmentNumber = segmentNumber;
          combinedSegmentSequence.push(segment);

          const frames = asArray(dataset.PerFrameFunctionalGroupsSequence);
          const bytes = pixelDataBytes(dataset.PixelData);
          const sourceBitCount = frameBitLength * frames.length;
          for (let bit = 0; bit < sourceBitCount; bit++) {
            writeBit(combinedPixelData, frameOffset * frameBitLength + bit, readBit(bytes, bit));
          }

          for (const frame of frames) {
            combinedFrameSequence.push(setFrameSegmentNumber(frame, segmentNumber));
          }

          frameOffset += frames.length;
          segmentNumber++;
        }

        return {
          dataset: {
            ...firstDataset,
            SegmentSequence: combinedSegmentSequence,
            PerFrameFunctionalGroupsSequence: combinedFrameSequence,
            NumberOfFrames: String(combinedFrameSequence.length),
            PixelData: combinedPixelData.buffer,
            SegmentsOverlap: combinedSegmentSequence.length > 1 ? 'YES' : 'NO',
          },
        };
      };

      let outputSegmentNumber = 0;
      let expectedFrameCount = 0;
      const labelmaps3D: any[] = [];
      const singleObjectLabelmaps3D: any[] = [];

      for (const sib of exportUnits) {
        const sibId = sib.segmentationId;
        const sibImageIds: string[] = (sib.representationData?.[LABELMAP] as any)?.imageIds ?? [];
        if (!sibImageIds.length) {
          continue;
        }
        const sibSegImages = sibImageIds.map((imageId: string) => cache.getImage(imageId));
        if (sibSegImages.length !== numFrames) {
          console.warn(
            `[nninter] export: object ${sibId} has ${sibSegImages.length} slices vs ${numFrames}; skipping (geometry mismatch)`
          );
          continue;
        }
        const csSeg: any = csToolsSegmentation.state.getSegmentation(sibId);
        const ohifSeg: any = segmentationService.getSegmentation(sibId);
        const representations = segmentationService.getRepresentationsForSegmentation(sibId);

        const labelmaps2D = makeEmptyLabelmaps2D();
        const sliceSegmentSets = labelmaps2D.map(() => new Set<number>());
        const sibReferencedImageIds = segReferencedImageIds(csSeg ?? ohifSeg ?? sib);
        let objectHadPixels = false;
        // A block unit's segment index is known by layout; only non-block units infer it from
        // pixel values. For a block, count ONLY its own value so stray foreign values (e.g. from
        // a pre-fix merged sync) can't flip the object's label/color or leak into its mask.
        const unitSegmentIndex: number | undefined = (sib as any).exportSegmentIndex;
        let localSegmentValue: number | undefined;

        for (let z = 0; z < sibSegImages.length; z++) {
          const segImage = sibSegImages[z];
          if (!segImage) {
            continue;
          }
          const src = segImage.getPixelData();
          const refImageId = segImage.referencedImageId ?? sibReferencedImageIds[z];
          const frameIndex =
            refImageId && refIndexByImageId.has(refImageId)
              ? (refIndexByImageId.get(refImageId) as number)
              : z;
          const dst = labelmaps2D[frameIndex];
          const onLabelmap = sliceSegmentSets[frameIndex];
          if (!dst?.pixelData || !onLabelmap) {
            continue;
          }

          for (let i = 0; i < src.length; i++) {
            const v = src[i];
            if (v !== 0 && (unitSegmentIndex === undefined || v === unitSegmentIndex)) {
              if (localSegmentValue === undefined) {
                localSegmentValue = v;
              }
              dst.pixelData[i] = 1;
              onLabelmap.add(1);
              objectHadPixels = true;
            }
          }
        }
        if (!objectHadPixels) {
          continue;
        }
        outputSegmentNumber++;

        labelmaps2D.forEach((labelmap2D: any, index: number) => {
          labelmap2D.segmentsOnLabelmap = Array.from(sliceSegmentSets[index]);
        });
        const objectFrameCount = labelmaps2D.filter(
          (labelmap2D: any) => labelmap2D.segmentsOnLabelmap.length
        ).length;
        expectedFrameCount += objectFrameCount;

        const localVal = unitSegmentIndex ?? localSegmentValue ?? 1;
        const segment: any =
          sib?.segments?.[localVal] ?? ohifSeg?.segments?.[localVal] ?? csSeg?.segments?.[localVal];
        const firstRepresentation = representations[0];
        let RecommendedDisplayCIELabValue = [0, 0, 0];
        try {
          const color =
            getObjectSegmentColor(csSeg ?? ohifSeg ?? sib, localVal) ??
            (firstRepresentation
              ? segmentationService.getSegmentColor(firstRepresentation.viewportId, sibId, localVal)
              : [255, 255, 255, 255]);
          RecommendedDisplayCIELabValue = dcmjs.data.Colors.rgb2DICOMLAB(
            color.slice(0, 3).map((value: number) => value / 255)
          ).map((value: number) => Math.round(value));
        } catch (e) {
          console.warn(`[nninter] export: color lookup failed for ${sibId}#${localVal}:`, e);
        }

        let segmentMetadata: any = {};
        const cachedData = (csSeg ?? sib)?.cachedStats?.data;
        if (cachedData !== undefined && cachedData.length > 1) {
          const found = cachedData
            .filter((e: any) => e !== undefined && e !== null)
            .find((e: any) => e.SegmentNumber == localVal);
          if (found !== undefined && Object.keys(found).length !== 0) {
            segmentMetadata = { ...found };
            segmentMetadata.SegmentLabel = segment?.label;
            segmentMetadata.RecommendedDisplayCIELabValue = RecommendedDisplayCIELabValue;
            segmentMetadata.SegmentAlgorithmType = 'SEMIAUTOMATIC';
          }
        }

        if (segmentMetadata === undefined || Object.keys(segmentMetadata).length === 0) {
          segmentMetadata = {
            SegmentLabel: segment?.label ?? `Object ${outputSegmentNumber}`,
            SegmentAlgorithmType: segment?.algorithmType || 'MANUAL',
            SegmentAlgorithmName: segment?.algorithmName || 'OHIF Brush',
            RecommendedDisplayCIELabValue,
            SegmentedPropertyCategoryCodeSequence: {
              CodeValue: 'T-D0050', CodingSchemeDesignator: 'SRT', CodeMeaning: 'Tissue',
            },
            SegmentedPropertyTypeCodeSequence: {
              CodeValue: 'T-D0050', CodingSchemeDesignator: 'SRT', CodeMeaning: 'Tissue',
            },
          };
        }

        if (segment?.cachedStats?.description !== undefined) {
          segmentMetadata.SegmentDescription = segment.cachedStats.description;
        }
        if (segment?.cachedStats?.algorithmName !== undefined) {
          segmentMetadata.SegmentAlgorithmName = segment.cachedStats.algorithmName;
        }
        if (segment?.cachedStats?.algorithmType !== undefined) {
          segmentMetadata.SegmentAlgorithmType = ['AUTOMATIC', 'SEMIAUTOMATIC', 'MANUAL'].includes(
            segment.cachedStats.algorithmType
          ) ? segment.cachedStats.algorithmType : 'SEMIAUTOMATIC';
        }
        segmentMetadata.SegmentNumber = outputSegmentNumber.toString();

        const labelmap3D = {
          segmentsOnLabelmap: [1],
          metadata: [undefined, segmentMetadata],
          labelmaps2D,
        };
        labelmaps3D.push(labelmap3D);
        singleObjectLabelmaps3D.push(labelmap3D);
      }

      if (!labelmaps3D.length) {
        throw new Error('No exportable labelmap data found');
      }

      let result = generateSEGFromLabelmap(referencedImages, labelmaps3D, metaData, options);
      const segmentSequenceLength = asArray(result?.dataset?.SegmentSequence).length;
      const frameSequenceLength = asArray(result?.dataset?.PerFrameFunctionalGroupsSequence).length;
      const generatedFrameCount = Number(result?.dataset?.NumberOfFrames ?? frameSequenceLength);
      if (
        labelmaps3D.length > 1 &&
        (segmentSequenceLength < labelmaps3D.length || generatedFrameCount < expectedFrameCount)
      ) {
        console.warn(
          `[nninter] adapter collapsed overlapping labelmaps ` +
            `(segments ${segmentSequenceLength}/${labelmaps3D.length}, ` +
            `frames ${generatedFrameCount}/${expectedFrameCount}); ` +
            'combining single-object SEG datasets manually.'
        );
        const singleObjectResults = singleObjectLabelmaps3D.map(labelmap3D =>
          generateSEGFromLabelmap(referencedImages, labelmap3D, metaData, options)
        );
        result = combineSingleObjectSegs(singleObjectResults);
      }

      try {
        if (result?.dataset) {
          result.dataset.SegmentsOverlap = labelmaps3D.length > 1 ? 'YES' : 'NO';
        }
      } catch (e) {
        console.warn('[nninter] export: could not set SegmentsOverlap:', e);
      }
      console.log(
        `[nninter/dbg] export result: objects=${labelmaps3D.length} ` +
        `SegmentSequence=${asArray(result?.dataset?.SegmentSequence).length} ` +
        `NumberOfFrames=${result?.dataset?.NumberOfFrames ?? '?'} ` +
        `SegmentsOverlap=${result?.dataset?.SegmentsOverlap}`
      );
      return result;
    },

    async downloadSegmentation({ segmentationId }) {
      const segmentationInOHIF = segmentationService.getSegmentation(segmentationId);
      const generatedSegmentation = await actions.generateSegmentation({ segmentationId });

      downloadDICOMData(generatedSegmentation.dataset, `${segmentationInOHIF.label}`);
    },

    async storeSegmentation({ segmentationId, dataSource }) {
      const segmentation = segmentationService.getSegmentation(segmentationId);

      if (!segmentation) {
        throw new Error('No segmentation found');
      }

      const { label } = segmentation;
      const defaultDataSource = dataSource ?? extensionManager.getActiveDataSource();
      const {
        value: reportName,
        dataSourceName: selectedDataSource,
        action,
      } = await createReportDialogPrompt({
        servicesManager,
        extensionManager,
        title: 'Store Segmentation',
      });

      if (action !== PROMPT_RESPONSES.CREATE_REPORT) {
        return;
      }

      try {
        const selectedDataSourceConfig = selectedDataSource
          ? extensionManager.getDataSources(selectedDataSource)[0]
          : defaultDataSource;
        const generatedData = await actions.generateSegmentation({
          segmentationId,
          options: {
            SeriesDescription: reportName || label || 'Research Derived Series',
          },
        });

        if (!generatedData || !generatedData.dataset) {
          throw new Error('Error during segmentation generation');
        }

        const { dataset: naturalizedReport } = generatedData;
        const selectedDataSourceConfigNew =
          selectedDataSourceConfig.store === undefined
            ? selectedDataSourceConfig[0]
            : selectedDataSourceConfig;

        await selectedDataSourceConfigNew.store.dicom(naturalizedReport);

        naturalizedReport.wadoRoot = selectedDataSourceConfigNew.getConfig().wadoRoot;
        DicomMetadataStore.addInstances([naturalizedReport], true);

        return naturalizedReport;
      } catch (error) {
        console.debug('Error storing segmentation:', error);
        throw error;
      }
    },

    async downloadNninterSegmentation({ segmentationId }) {
      return actions.downloadSegmentation({ segmentationId });
    },

    async storeNninterSegmentation({ segmentationId, dataSource }) {
      return actions.storeSegmentation({ segmentationId, dataSource });
    },

    setAiToolActive: ({ toolName }: { toolName: string }) => {
      if (!toolName) {
        return;
      }

      if (toolboxState.getLocked() && toolName !== 'Pan') {
        return commandsManager.run('setToolActive', { toolName: 'Pan' });
      }

      return commandsManager.run('setToolActive', { toolName });
    },

    runAiSegmentation: () => {
      if (toolboxState.getLocked()) {
        return;
      }

      return commandsManager.run('nninter');
    },

    async initNninter( options: {viewportId: string} = {viewportId: undefined} ){

      let { activeViewportId, viewports } = viewportGridService.getState();
      if(options.viewportId !== undefined){
        activeViewportId = options.viewportId;
      }
      const activeViewportSpecificData = viewports.get(activeViewportId);
      if(activeViewportSpecificData === undefined){
        return;
      }
      const { displaySetInstanceUIDs } = activeViewportSpecificData;
      const displaySets = displaySetService.activeDisplaySets;
      const displaySetInstanceUID = displaySetInstanceUIDs[0];
      let currentDisplaySets;
      for (let i = 0; i < displaySets.length; i++) {
        if (displaySets[i].displaySetInstanceUID == displaySetInstanceUID) {
          currentDisplaySets = displaySets[i];
          break; // Exit early once found
        }
      }
      if(currentDisplaySets === undefined || currentDisplaySets.Modality === "SEG"){
        return;
      }

      // Detect series change — used both for posNeg reset and notification gating.
      const _seriesChanged = currentDisplaySets.SeriesInstanceUID !== _lastInitSeries;
      if (_seriesChanged) {
        _lastInitSeries = currentDisplaySets.SeriesInstanceUID;
        toolboxState.setPosNeg(false);
      }

      let url = `/nninteractive/infer/segmentation?image=${currentDisplaySets.SeriesInstanceUID}&output=dicom_seg`;
      let params = {
        largest_cc: false,
        result_extension: '.nii.gz',
        result_dtype: 'uint16',
        result_compress: false,
        studyInstanceUID: currentDisplaySets.StudyInstanceUID,
        restore_label_idx: false,
        nninter: "init",
      };

      // Show notification only on the first initNninter for a new series.
      // _seriesChanged is false for all repeat triggers (other MPR panes loading the
      // same series, viewport-type switches stack↔volume, active-viewport clicks, etc.)
      // so a single _seriesChanged gate is sufficient — no need to check viewport type.
      const _showNotification = _seriesChanged;

      let data = constructInferenceFormData(params, null);
      const _initKey = `${currentDisplaySets.StudyInstanceUID}|${currentDisplaySets.SeriesInstanceUID}`;

      if (_pendingInitPromise && _pendingInitKey === _initKey) {
        return _pendingInitPromise;
      }

      const recoverInitializedSession = async (error: any) => {
        const statusUrl = withNnInteractiveClientSession(
          `/nninteractive/infer/session?image=${currentDisplaySets.SeriesInstanceUID}&studyInstanceUID=${currentDisplaySets.StudyInstanceUID}`
        );
        const statusResponse = await axios.get(statusUrl);
        if (statusResponse?.data?.active) {
          console.warn('Init nninter response failed, but session is active; continuing.', error);
          return statusResponse;
        }
        throw error;
      };

      // Create the axios promise
      const requestPromise = axios.post(url, data, {
        responseType: 'arraybuffer',
        headers: {
          accept: 'application/json, multipart/form-data',
        },
      }).catch(recoverInitializedSession);

      const initPromise = requestPromise.finally(() => {
        if (_pendingInitPromise === initPromise) {
          _pendingInitPromise = undefined;
          _pendingInitKey = undefined;
        }
      });
      _pendingInitKey = _initKey;
      _pendingInitPromise = initPromise;

      if (_showNotification) {
        uiNotificationService.show({
          title: 'NNInit',
          message: 'Initializing nninter...',
          type: 'info',
          promise: initPromise,
          promiseMessages: {
            loading: 'Initializing nninter...',
            success: () => 'Init nninter - Successful',
            error: (error) => `Init nninter - Failed: ${error.message || 'Unknown error'}`,
          },
        });
      }

      try {
        const response = await initPromise;
        if (response.status === 200) {
          // Mark the session live so the AI toolbox enables prompts/tools.
          toolboxState.setSessionActive(true);
          toolboxState.setSessionSeries(currentDisplaySets.SeriesInstanceUID);
          // Fresh backend session holds no object yet.
          _serverObjectId = undefined;
          return response;
        }
      } catch (error) {
        toolboxState.setSessionActive(false);
        console.error('Init nninter error:', error);
        throw error;
      }

    },
    /**
     * Poll the proxy for whether a live backend session exists for the active
     * series (without creating one). Keeps toolboxState.sessionActive in sync so
     * the UI can gate prompts, and doubles as the browser→proxy heartbeat.
     */
    async nninterSessionStatus() {
      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      if (!activeViewportSpecificData) {
        return false;
      }
      const { displaySetInstanceUIDs } = activeViewportSpecificData;
      const displaySets = displaySetService.activeDisplaySets;
      const currentDisplaySets = displaySets.filter(
        e => e.displaySetInstanceUID == displaySetInstanceUIDs[0]
      )[0];
      if (!currentDisplaySets || currentDisplaySets.Modality === 'SEG') {
        return false;
      }
      try {
        const url = withNnInteractiveClientSession(
          `/nninteractive/infer/session?image=${currentDisplaySets.SeriesInstanceUID}&studyInstanceUID=${currentDisplaySets.StudyInstanceUID}`
        );
        const response = await axios.get(url);
        const active = !!response?.data?.active;
        toolboxState.setSessionActive(active);
        if (active) {
          toolboxState.setSessionSeries(currentDisplaySets.SeriesInstanceUID);
        }
        return active;
      } catch (error) {
        // A transient network error shouldn't tear down a session the user is
        // mid-interaction with; leave sessionActive as-is.
        console.warn('nninter session status check failed:', error);
        return toolboxState.getSessionActive();
      }
    },
    /**
     * Release the backend lease when the user leaves the page. Uses keepalive fetch
     * with credentials so the request passes through the authenticated ingress.
     */
    closeNninterSession() {
      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      if (!activeViewportSpecificData) {
        return;
      }
      const { displaySetInstanceUIDs } = activeViewportSpecificData;
      const displaySets = displaySetService.activeDisplaySets;
      const currentDisplaySets = displaySets.filter(
        e => e.displaySetInstanceUID == displaySetInstanceUIDs[0]
      )[0];
      if (!currentDisplaySets) {
        return;
      }
      const url = withNnInteractiveClientSession(
        `/nninteractive/infer/close?image=${currentDisplaySets.SeriesInstanceUID}&studyInstanceUID=${currentDisplaySets.StudyInstanceUID}`
      );
      toolboxState.setSessionActive(false);
      try {
        const body = new FormData();
        body.append('image', currentDisplaySets.SeriesInstanceUID);
        body.append('studyInstanceUID', currentDisplaySets.StudyInstanceUID);
        body.append('clientSessionID', getNnInteractiveClientSessionId());
        fetch(url, {
          method: 'POST',
          body,
          keepalive: true,
          credentials: 'include',
        }).catch(() => {});
      } catch (error) {
        console.warn('closeNninterSession failed:', error);
      }
    },
    async undoNninter() {
      if (toolboxState.getLocked()) {
        return;
      }
      const start = Date.now();
      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      const { displaySetInstanceUIDs } = activeViewportSpecificData;
      const displaySets = displaySetService.activeDisplaySets;
      const displaySetInstanceUID = displaySetInstanceUIDs[0];
      const currentDisplaySets = displaySets.filter(
        e => e.displaySetInstanceUID == displaySetInstanceUID
      )[0];

      // Locate the active nnInteractive segmentation for this series.
      const { segmentationService, cornerstoneViewportService } = servicesManager.services;
      const activeSegmentation = segmentationService.getActiveSegmentation(activeViewportId);
      const activeSegmentObj = segmentationService.getActiveSegment(activeViewportId);
      if (!activeSegmentation || !activeSegmentObj) {
        return;
      }
      const segmentationId = activeSegmentation.segmentationId;
      const segmentNumber = activeSegmentObj.segmentIndex;
      const segImageIds: string[] =
        (csToolsSegmentation.state.getSegmentation(segmentationId)
          ?.representationData?.Labelmap as any)?.imageIds ?? [];
      if (segImageIds.length === 0) {
        return;
      }
      // Per-object model: the active segmentation IS this object's whole labelmap (single map).
      const _undoBlockIds = segImageIds;
      console.log(`[nninter/dbg] undo: object ${segmentationId} map=${_undoBlockIds.length}`);

      const url = `/nninteractive/infer/segmentation?image=${currentDisplaySets.SeriesInstanceUID}&output=dicom_seg`;
      const params = {
        largest_cc: false,
        result_extension: '.nii.gz',
        result_dtype: 'uint16',
        result_compress: false,
        studyInstanceUID: currentDisplaySets.StudyInstanceUID,
        restore_label_idx: false,
        nninter: 'undo',
      };
      const data = constructInferenceFormData(params, null);

      const beforePost = Date.now();
      const undoPromise = axios.post(url, data, {
        responseType: 'arraybuffer',
        headers: { accept: 'application/octet-stream' },
      });

      uiNotificationService.show({
        title: 'nnInteractive',
        message: 'Undoing last interaction...',
        type: 'info',
        promise: undoPromise,
        promiseMessages: {
          loading: 'Undoing last interaction...',
          error: error => `Undo - Failed: ${error.message || 'Unknown error'}`,
        },
      });

      try {
        const response = await undoPromise;
        const afterPost = Date.now();
        if (response.status !== 200) {
          return;
        }
        const ct = response.headers['content-type'] as string;
        // allowEmptySeg: undoing the only interaction restores an empty segment,
        // which arrives as a zero-length seg part.
        const { meta, seg } = await parseMultipart(response.data, ct, { allowEmptySeg: true });
        const afterParse = Date.now();

        // --- round-trip timing breakdown (mirrors the normal nninter path) ---
        const networkRoundTripMs = afterPost - beforePost;
        const sRequestTs = metaNum(meta as Record<string, unknown>, 'server_request_ts');
        const sBeginTs   = metaNum(meta as Record<string, unknown>, 'server_begin_ts');
        const sEndTs     = metaNum(meta as Record<string, unknown>, 'server_end_ts');
        const sUndoCore  = metaNum(meta as Record<string, unknown>, 'nninter_core_elapsed');
        const sResult    = metaNum(meta as Record<string, unknown>, 'server_result_elapsed');
        const postInFlightMs     = (sRequestTs != null) ? sRequestTs * 1000 - beforePost : undefined;
        const nninteractivePrepMs        = (sRequestTs != null && sBeginTs != null) ? (sBeginTs - sRequestTs) * 1000 : undefined;
        const serverProcessMs    = (sBeginTs != null && sEndTs != null) ? (sEndTs - sBeginTs) * 1000 : undefined;
        const responseInFlightMs = (sEndTs != null) ? afterPost - sEndTs * 1000 : undefined;
        console.log(
          `[nninter undo timing]\n` +
          `  client → undoNninter():          ${((beforePost - start) / 1000).toFixed(3)}s\n` +
          `  ── round-trip total:              ${(networkRoundTripMs / 1000).toFixed(3)}s\n` +
          (postInFlightMs     != null ? `     POST in flight:               ${(postInFlightMs / 1000).toFixed(3)}s\n` : '') +
          (nninteractivePrepMs        != null ? `     nnInteractive pre-processing:          ${(nninteractivePrepMs / 1000).toFixed(3)}s\n` : '') +
          (serverProcessMs    != null ? `     server processing (undo):      ${(serverProcessMs / 1000).toFixed(3)}s\n` : '') +
          (sUndoCore != null ? `       ↳ session.undo():            ${sUndoCore.toFixed(3)}s\n` : '') +
          (sResult   != null ? `       ↳ result retrieve:           ${sResult.toFixed(3)}s\n` : '') +
          (responseInFlightMs != null ? `     response in flight:            ${(responseInFlightMs / 1000).toFixed(3)}s\n` : '') +
          `  client parse multipart:          ${((afterParse - afterPost) / 1000).toFixed(3)}s`
        );

        const undone = String((meta as any).undone).toLowerCase() === 'true';
        if (!undone) {
          uiNotificationService.show({
            title: 'nnInteractive',
            message: 'Nothing to undo',
            type: 'info',
          });
          return;
        }

        const flipped = String((meta as any).flipped).toLowerCase() === 'true';
        const predOffset: number[] = JSON.parse((meta as any).pred_offset || '[0,0,0]');
        const predFull: number[] = JSON.parse((meta as any).pred_full_shape || '[]');
        const predCrop: number[] = JSON.parse((meta as any).pred_crop_shape || '[]');
        const cropBytes = new Uint8Array(seg);

        let _hasCropGeom = false;
        let _segZ0 = 0, _segZ1 = 0, _cropY = 0, _cropX = 0, _y0 = 0, _x0 = 0, _fullX = 0;
        if (predFull.length === 3 && predCrop.length === 3 && predCrop.every(v => v > 0)) {
          const [, , fullX] = predFull;
          const [cropZ, cropY, cropX] = predCrop;
          const [z0, y0, x0] = predOffset;
          _segZ0 = z0; _segZ1 = z0 + cropZ;
          _cropY = cropY; _cropX = cropX;
          _y0 = y0; _x0 = x0; _fullX = fullX;
          _hasCropGeom = true;
        }

        let merged = _undoBlockIds.map(imageId => cache.getImage(imageId));
        if (flipped) merged.reverse();

        // Pass 1: clear all voxels of the active segment (use dirtySlices when available).
        const prevStats = (activeSegmentation.segments?.[segmentNumber] as any)?.cachedStats;
        const prevDirty: number[] | undefined = prevStats?.dirtySlices;
        const clearSlice = (arrIdx: number) => {
          const vm = merged[arrIdx]?.voxelManager;
          if (!vm) return;
          const sd = vm.getScalarData();
          for (let j = 0; j < sd.length; j++) {
            if (sd[j] !== 0) sd[j] = 0;
          }
        };
        if (prevDirty?.length) {
          for (const origIdx of prevDirty) {
            clearSlice(flipped ? merged.length - 1 - origIdx : origIdx);
          }
        } else {
          for (let i = 0; i < merged.length; i++) clearSlice(i);
        }

        // Pass 2: write the restored crop (skipped entirely when the object is now empty).
        const z_range: number[] = [];
        if (_hasCropGeom) {
          for (let i = _segZ0; i < _segZ1; i++) {
            const sd = merged[i].voxelManager.getScalarData();
            const c = i - _segZ0;
            const cropSliceBase = c * _cropY * _cropX;
            let wrote = false;
            for (let cy = 0; cy < _cropY; cy++) {
              const srcRow = cropSliceBase + cy * _cropX;
              const dstRow = (_y0 + cy) * _fullX + _x0;
              for (let cx = 0; cx < _cropX; cx++) {
                if (cropBytes[srcRow + cx] === 1) {
                  sd[dstRow + cx] = segmentNumber;
                  wrote = true;
                }
              }
            }
            if (wrote) z_range.push(flipped ? merged.length - i - 1 : i);
          }
        }
        if (flipped) merged.reverse();

        // Keep cachedStats.dirtySlices in sync so the next interaction clears correctly.
        if ((activeSegmentation.segments?.[segmentNumber] as any)?.cachedStats) {
          (activeSegmentation.segments[segmentNumber] as any).cachedStats.dirtySlices = z_range;
          (activeSegmentation.segments[segmentNumber] as any).cachedStats.segZ0 = _hasCropGeom ? _segZ0 : 0;
          (activeSegmentation.segments[segmentNumber] as any).cachedStats.segZ1 = _hasCropGeom ? _segZ1 : merged.length;
        }

        // Remove the most-recently-added prompt measurement for this series.
        const AI_PROMPT_TOOLS = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'];
        const promptsForSeries = measurementService
          .getMeasurements()
          .filter(
            m =>
              AI_PROMPT_TOOLS.includes(m.toolName) &&
              m.referenceSeriesUID === currentDisplaySets.SeriesInstanceUID
          );
        const lastPrompt = promptsForSeries[promptsForSeries.length - 1];
        if (lastPrompt?.uid) {
          measurementService.removeMany([lastPrompt.uid]);
        }

        // Repaint.
        const activeVp = cornerstoneViewportService.getCornerstoneViewport(activeViewportId);
        (activeVp as any)?.render?.();
        eventTarget.dispatchEvent(
          new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
            detail: { segmentationId },
          })
        );
        console.log(`[nninter undo timing] total client: ${((Date.now() - start) / 1000).toFixed(3)}s`);
        uiNotificationService.show({
          title: 'nnInteractive',
          message: 'Undo - Successful',
          type: 'success',
        });
        return response;
      } catch (error) {
        if (_isSessionExpiredError(error)) {
          toolboxState.setSessionActive(false);
          uiNotificationService?.show({
            title: 'nnInteractive',
            message: 'Session expired — please Initialize again.',
            type: 'warning',
          });
        }
        console.error('Undo nninter error:', error);
        throw error;
      }
    },

    async resetNninter(options: {clearMeasurements: boolean} = {clearMeasurements: false}){
      if (toolboxState.getLocked()) {
        return;
      }

      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      const { displaySetInstanceUIDs } = activeViewportSpecificData;
      const displaySets = displaySetService.activeDisplaySets;
      const displaySetInstanceUID = displaySetInstanceUIDs[0];
      const currentDisplaySets = displaySets.filter(e => {
        return e.displaySetInstanceUID == displaySetInstanceUID;
      })[0];
      let url = `/nninteractive/infer/segmentation?image=${currentDisplaySets.SeriesInstanceUID}&output=dicom_seg`;
      let params = {
        largest_cc: false,
        result_extension: '.nii.gz',
        result_dtype: 'uint16',
        result_compress: false,
        studyInstanceUID: currentDisplaySets.StudyInstanceUID,
        restore_label_idx: false,
        nninter: "reset",
      };

      let data = constructInferenceFormData(params, null);

      // Create the axios promise
      const resetPromise = axios.post(url, data, {
        responseType: 'arraybuffer',
        headers: {
          accept: 'application/json, multipart/form-data',
        },
      });

      try {
        const response = await resetPromise;
        if (response.status === 200) {
          // Backend target buffer + interactions were wiped; it no longer holds any object.
          _serverObjectId = undefined;
          if (options.clearMeasurements) {
            commandsManager.run('clearMeasurements')
          }
          return response;
        }
      } catch (error) {
        if (_isSessionExpiredError(error)) {
          toolboxState.setSessionActive(false);
        }
        console.error('Reset nninter error:', error);
        throw error;
      }
    },
    async resetSegment({ segmentationId, segmentIndex }: { segmentationId: string; segmentIndex: number }) {
      const segmentation = csToolsSegmentation.state.getSegmentation(segmentationId);
      const imageIds: string[] = (segmentation?.representationData?.Labelmap as any)?.imageIds ?? [];

      const _zeroImageId = (imageId: string) => {
        const image = cache.getImage(imageId);
        if (!image) return;
        const vm = image.voxelManager as csTypes.IVoxelManager<number>;
        const scalarData = vm.getScalarData();
        if (!scalarData.some((v: number) => v === segmentIndex)) return;
        for (let j = 0; j < scalarData.length; j++) {
          if (scalarData[j] === segmentIndex) scalarData[j] = 0;
        }
        vm.setScalarData(scalarData);
      };

      // 1. Find the labelmap actors currently in the active viewport.
      //    Using referencedId (the actor's imageId) avoids the flipped-series
      //    index mismatch that caused the "vague then gone" two-step.
      const { activeViewportId } = viewportGridService.getState();
      const activeVp = servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(activeViewportId);
      const allActors: any[] = (activeVp as any)?.getActors?.() ?? [];
      const labelmapActors = allActors.filter((a: any) =>
        a.representationUID?.startsWith(`${segmentationId}-Labelmap`)
      );
      const visibleImageIds = new Set(labelmapActors.map((a: any) => a.referencedId).filter(Boolean));

      // 2. Zero the visible slice(s) and synchronously push the zeroed data into
      //    VTK's internal buffer + force an immediate WebGL render.
      //    Bypasses the rAF event queue → no intermediate "vague" frame.
      for (const actorEntry of labelmapActors) {
        const imageId = actorEntry.referencedId;
        if (!imageId) continue;
        _zeroImageId(imageId);
        const inputData = actorEntry.actor?.getMapper?.()?.getInputData?.();
        if (inputData) {
          const csImage = cache.getImage(imageId);
          if (csImage) {
            const pixelData = csImage.voxelManager?.getScalarData?.();
            const vtkScalars = inputData.getPointData?.()?.getScalars?.();
            const vtkData = vtkScalars?.getData?.();
            if (pixelData && vtkData && vtkData.length === pixelData.length) {
              vtkData.set(pixelData);
              vtkScalars?.modified();
              inputData.modified();
            }
          }
          actorEntry.actor?.modified?.();
          actorEntry.actor?.getMapper?.()?.modified?.();
        }
      }
      (activeVp as any)?.render?.();   // synchronous WebGL render — instant visual removal

      // 3. Background: zero all remaining slices, remove measurements, reset server.
      setTimeout(() => {
        for (const imageId of imageIds) {
          if (!visibleImageIds.has(imageId)) _zeroImageId(imageId);
        }
        const measurementUIDs = measurementService
          .getMeasurements()
          .filter(e => e?.metadata?.segmentationId === segmentationId && e?.metadata?.SegmentNumber === segmentIndex)
          .map(e => e?.uid);
        if (measurementUIDs.length > 0) measurementService.removeMany(measurementUIDs);
        commandsManager.run('resetNninter', { clearMeasurements: false }).catch(() => {});
        eventTarget.dispatchEvent(
          new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, { detail: { segmentationId } })
        );
      }, 0);
    },
    /**
     * Load an existing segment into the nnInteractive backend as the CURRENT object, so the user can
     * keep refining it with new prompts. Uploads the segment's current mask via the proxy's `set_mask`
     * mode (which resets interactions + sets the server target buffer), then marks it the active
     * segment WITHOUT a reset-first so the next prompt refines rather than restarts. Works for
     * nnInteractive segments and (best-effort) for opened DICOM-SEG segments whose labelmap covers the
     * source series. Triggered on segment selection in the panel; silent no-op if no live session.
     */
    async loadSegmentForRefinement({ segmentationId, segmentIndex }: { segmentationId: string; segmentIndex: number }) {
      if (toolboxState.getLocked()) {
        return;
      }
      if (!segmentationId || segmentIndex == null) {
        return;
      }

      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      if (!activeViewportSpecificData) {
        return;
      }
      const displaySetInstanceUID = activeViewportSpecificData.displaySetInstanceUIDs?.[0];
      const displaySets = displaySetService.activeDisplaySets;
      const currentDisplaySets = displaySets.find(e => e.displaySetInstanceUID === displaySetInstanceUID);
      // Need the SOURCE (CT) series in the active viewport to target its session.
      if (!currentDisplaySets || currentDisplaySets.Modality === 'SEG') {
        return;
      }
      // A live backend session for this series is required (set_mask resets/sets its target buffer).
      // If the user selects an existing/imported object first, initialize on demand so the click really
      // makes that object refinement-ready.
      if (!toolboxState.getSessionActive()) {
        try {
          await actions.initNninter({ viewportId: activeViewportId });
        } catch (error) {
          console.warn('[nninter] loadSegmentForRefinement: init before set_mask failed:', error);
          return;
        }
        if (!toolboxState.getSessionActive()) {
          return;
        }
      }

      const segState = csToolsSegmentation.state.getSegmentation(segmentationId);
      const segStackImageIds: string[] =
        (segState?.representationData?.[LABELMAP] as any)?.imageIds ?? [];
      const _lsfrSegCount = segState ? Object.keys(segState.segments ?? {}).length : 0;
      console.log(
        `[nninter/dbg] loadSegmentForRefinement: segmentationId=${segmentationId} segmentIndex=${segmentIndex} ` +
        `segmentsInThisSegmentation=${_lsfrSegCount} ` +
        `${_lsfrSegCount > 1 ? '(MULTI-SEGMENT — likely an imported SEG; refine model expects 1 object/segmentation)' : '(single-object)'} ` +
        `stackImgs=${segStackImageIds.length}`
      );
      // For a multi-segment (imported) labelmap, reveal the block/value layout so we can write refines
      // into the correct segment block. Also report which images actually hold the clicked segmentIndex.
      if (segStackImageIds.length > (currentDisplaySets.imageIds?.length ?? 0)) {
        dumpLabelmapLayout(segState);
      }
      if (!segStackImageIds.length) {
        uiNotificationService.show({
          title: 'nnInteractive',
          message: 'This segmentation has no per-slice labelmap to load for refinement.',
          type: 'warning',
        });
        return;
      }

      const ctImageIds: string[] = currentDisplaySets.imageIds ?? [];
      const numSlices = ctImageIds.length;
      const idxByCtImageId = new Map<string, number>();
      for (let i = 0; i < numSlices; i++) {
        idxByCtImageId.set(ctImageIds[i], i);
      }

      const firstSeg = cache.getImage(segStackImageIds[0]);
      const rows = firstSeg?.rows;
      const cols = firstSeg?.columns;
      if (!rows || !cols || !numSlices) {
        console.warn('[nninter] loadSegmentForRefinement: could not resolve mask geometry');
        return;
      }
      const sliceLen = rows * cols;

      // Build the full-volume mask in SOURCE display-set (InstanceNumber) slice order. The proxy
      // reshapes to (z,y,x) and reverses z when the series is flipped — the same convention the
      // inference write path uses — so display-set order is correct here. Each labelmap slice is
      // placed at its source slice's display-set index via referencedImageId (positional fallback).
      const mask = new Uint8Array(numSlices * sliceLen);
      const dirty: number[] = [];
      let voxelCount = 0;
      // Per-object model: a segmentation with exactly S images is a single binary object (value 1) —
      // read ALL nonzero voxels. Fall back to value-matching for a not-yet-split multi-block labelmap.
      const _isPerObject = segStackImageIds.length === numSlices;
      // The active segment index to drive: always 1 for a per-object segmentation.
      const _effIndex = _isPerObject ? 1 : segmentIndex;
      for (let i = 0; i < segStackImageIds.length; i++) {
        const segImg: any = cache.getImage(segStackImageIds[i]);
        if (!segImg) continue;
        const refId: string | undefined = segImg.referencedImageId;
        let z = refId != null && idxByCtImageId.has(refId) ? (idxByCtImageId.get(refId) as number) : i;
        if (z < 0 || z >= numSlices) continue;
        const sd = (segImg.voxelManager as csTypes.IVoxelManager<number>)?.getScalarData?.();
        if (!sd || sd.length !== sliceLen) continue;
        const base = z * sliceLen;
        let any = false;
        for (let j = 0; j < sliceLen; j++) {
          if (_isPerObject ? sd[j] !== 0 : sd[j] === segmentIndex) {
            mask[base + j] = 1;
            voxelCount++;
            any = true;
          }
        }
        if (any) dirty.push(z);
      }

      if (voxelCount === 0) {
        // Empty object — nothing to load. Make it active and force the next prompt to reset the
        // backend fresh (it may still hold another object) by clearing the tracked server object.
        try {
          await commandsManager.run('setActiveSegmentation', { segmentationId });
        } catch (error) {
          console.warn(`[nninter] loadSegmentForRefinement: could not activate ${segmentationId}:`, error);
        }
        segmentationService.setActiveSegment(segmentationId, _effIndex);
        toolboxState.setCurrentActiveSegment(_effIndex);
        toolboxState.setRefineNew(false);
        _serverObjectId = undefined;
        return;
      }

      const url = `/nninteractive/infer/segmentation?image=${currentDisplaySets.SeriesInstanceUID}&output=dicom_seg`;
      const params = {
        largest_cc: false,
        result_extension: '.nii.gz',
        result_dtype: 'uint16',
        result_compress: false,
        studyInstanceUID: currentDisplaySets.StudyInstanceUID,
        restore_label_idx: false,
        nninter: 'set_mask',
      };
      const data = constructInferenceFormData(params, [
        { name: 'mask', data: new Blob([mask]), fileName: 'mask.raw' },
      ]);

      const loadPromise = axios.post(url, data, {
        responseType: 'arraybuffer',
        headers: { accept: 'application/octet-stream' },
      });

      uiNotificationService.show({
        title: 'nnInteractive',
        message: `Loading Segment ${segmentIndex} for refinement…`,
        type: 'info',
        promise: loadPromise,
        promiseMessages: {
          loading: `Loading Segment ${segmentIndex} for refinement…`,
          success: () => `Segment ${segmentIndex} ready — draw prompts to refine it`,
          error: error => `Load segment failed: ${error.message || 'Unknown error'}`,
        },
      });

      try {
        const response = await loadPromise;
        if (response.status !== 200) {
          return;
        }

        // Make this the active segment and mark it current so the NEXT prompt refines (no reset-first,
        // and not a new-object). refineNew=false ensures nninter() refines this segment rather than
        // creating a new one even if the user had just armed "next object".
        try {
          await commandsManager.run('setActiveSegmentation', { segmentationId });
        } catch (error) {
          console.warn(`[nninter] loadSegmentForRefinement: could not activate ${segmentationId}:`, error);
        }
        segmentationService.setActiveSegment(segmentationId, _effIndex);
        toolboxState.setCurrentActiveSegment(_effIndex);
        toolboxState.setRefineNew(false);
        // The backend now holds THIS segment's mask (set_mask). The next prompt refines it without a
        // reset (which would wipe the just-loaded mask).
        _serverObjectId = serverObjKey(segmentationId, _effIndex);

        // Prime the refine clear so the next inference removes this segment's current voxels before
        // writing the refined result. dirtySlices gives the fast path; segZ0/segZ1 force a full-range
        // value-based clear fallback (order-independent) if the fast path can't resolve slices.
        // Set it on the object nninter's refine path reads (segmentationService.getActiveSegmentation),
        // falling back to the cs-tools state segmentation.
        const activeSegForStats = segmentationService.getActiveSegmentation(activeViewportId);
        const segObj = (activeSegForStats?.segments?.[_effIndex] ??
          segState?.segments?.[_effIndex]) as any;
        if (segObj) {
          segObj.cachedStats = segObj.cachedStats || {};
          segObj.cachedStats.dirtySlices = dirty;
          segObj.cachedStats.segZ0 = 0;
          segObj.cachedStats.segZ1 = numSlices;
        }
      } catch (error) {
        if (_isSessionExpiredError(error)) {
          toolboxState.setSessionActive(false);
          uiNotificationService?.show({
            title: 'nnInteractive',
            message: 'Session expired — please Initialize again.',
            type: 'warning',
          });
        }
        console.error('loadSegmentForRefinement error:', error);
      }
    },
    async nninter(textPrompts?: string | string[]) {
      if (toolboxState.getLocked()) {
        return;
      }

      const start = Date.now();

      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);

      const currentImageIdIndex = getCurrentStackImageIdIndex(activeViewportId);
      const { displaySetInstanceUIDs } = activeViewportSpecificData;

      const displaySets = displaySetService.activeDisplaySets;

      const displaySetInstanceUID = displaySetInstanceUIDs[0];
      const currentDisplaySets = displaySets.find(e => e.displaySetInstanceUID === displaySetInstanceUID);
      if (!currentDisplaySets) return;
      const currentMeasurements = measurementService
        .getMeasurements()
        .filter((measurement: any) => !measurement.metadata?.manualCorrection);

      const unAssignedMeasurements = currentMeasurements.filter(e => {
          return e.metadata.SegmentNumber === undefined;
        })


      const _seriesUID = currentDisplaySets.SeriesInstanceUID;
      const activeSegmentation = servicesManager.services.segmentationService.getActiveSegmentation(activeViewportId);

      // ── Per-object segmentation resolution ───────────────────────────────────────────────────
      // Each OBJECT is its own Cornerstone segmentation (single segment, index 1, single S-image
      // labelmap holding value 1). A new object → a fresh segmentation; refine → the active
      // sibling. This makes overlap native (one actor per object) and MPR sync a 1:1 copy.
      const _sliceCount = (currentDisplaySets.imageIds ?? []).length;
      const _siblings = seriesSegmentations(_seriesUID);
      const activeSegmentObj = servicesManager.services.segmentationService.getActiveSegment(activeViewportId);

      let segmentationId = `${csUtils.uuidv4()}`;
      const segmentNumber = 1; // ALWAYS 1 in the per-object model
      let mode: 'new-segmentation' | 'refine' = 'new-segmentation';
      let segments: { [segmentIndex: string]: cstTypes.Segment } = {};
      let existingSegments: { [segmentIndex: string]: cstTypes.Segment } = {};
      let priorImageIds: string[] = [];
      const _activeIsSibling =
        !!activeSegmentation &&
        _siblings.some((s: any) => s.segmentationId === activeSegmentation.segmentationId);
      if (!toolboxState.getRefineNew() && _activeIsSibling) {
        segmentationId = activeSegmentation.segmentationId;
        const segState = getSegmentationStateById(segmentationId);
        existingSegments = segState?.segments ?? {};
        segments = existingSegments;
        priorImageIds = (segState?.representationData?.[LABELMAP] as any)?.imageIds ?? [];
        mode = 'refine';
      }
      const existing = mode === 'refine';
      // Ordinal names/colors a NEW object; a refined object keeps its stored label/color.
      const _objectOrdinal = existing
        ? Math.max(1, _siblings.findIndex((s: any) => s.segmentationId === segmentationId) + 1)
        : _siblings.length + 1;
      // Tag freshly-drawn (unassigned) prompts with THIS object. The prompt-collection loop isolates
      // an object's prompts by (segmentationId, SegmentNumber=1).
      for (const e of unAssignedMeasurements) {
        e.metadata.SegmentNumber = segmentNumber;
        e.metadata.segmentationId = segmentationId;
      }
      // reset_first wipes the backend before applying prompts — needed whenever it is not already
      // holding THIS object (a new object, or a switch not preceded by a set_mask load). Continued
      // prompts on the same object accumulate (reset_first = false) → a negative prompt can shrink it.
      const _needsReset = _serverObjectId !== serverObjKey(segmentationId, segmentNumber);
      console.log(
        `[nninter/dbg] resolve: refineNew=${toolboxState.getRefineNew()} ` +
        `activeSeg=${activeSegmentation?.segmentationId ?? 'none'} activeSegIdx=${activeSegmentObj?.segmentIndex ?? 'none'} ` +
        `=> mode=${mode} target=${segmentationId} ordinal=${_objectOrdinal} siblings=${_siblings.length} ` +
        `priorImgs=${priorImageIds.length} sliceCount=${_sliceCount} ` +
        `serverObjectId=${_serverObjectId ?? 'none'} reset_first=${_needsReset}`
      );


      const pos_points: any[] = [];
      const neg_points: any[] = [];
      const pos_boxes: any[] = [];
      const neg_boxes: any[] = [];
      const pos_lassos: any[] = [];
      const neg_lassos: any[] = [];
      const pos_scribbles: any[] = [];
      const neg_scribbles: any[] = [];
      const probe2Labels: string[] = [];
      const seriesUID = currentDisplaySets.SeriesInstanceUID;
      const activeViewport = cornerstoneViewportService.getCornerstoneViewport(activeViewportId);
      // The proxy expects z in the source display-set (InstanceNumber) slice order. For MPR/volume
      // viewports the coordinate helpers convert the volume's geometric k → this order using these ids.
      const seriesImageIds: string[] = currentDisplaySets.imageIds ?? [];
      for (const e of currentMeasurements) {
        // Every object uses SegmentNumber 1, so the discriminator across objects is segmentationId.
        // Isolate THIS segment's prompts: same segmentation AND same segment number.
        if (e.referenceSeriesUID !== seriesUID || e.metadata.segmentationId !== segmentationId ||
            e.metadata.SegmentNumber !== segmentNumber) continue;
        const isNeg = !!e.metadata.neg;
        if (e.toolName === 'Probe2') {
          const index = getPromptPointIJK(e, activeViewport, seriesImageIds);
          if (!index) {
            continue;
          }
          (isNeg ? neg_points : pos_points).push(index);
          if (!isNeg && !textPrompts) probe2Labels.push(e.label);
        } else if (e.toolName === 'RectangleROI2') {
          const box = getRectangleBoxIJK(e, activeViewport, seriesImageIds);
          if (!box?.length) {
            continue;
          }
          (isNeg ? neg_boxes : pos_boxes).push(box);
        } else if (e.toolName === 'PlanarFreehandROI3') {
          const b = getClosedFreehandBoundaryIJK(e, activeViewport, seriesImageIds);
          if (b) (isNeg ? neg_lassos : pos_lassos).push(b);
        } else if (e.toolName === 'PlanarFreehandROI2') {
          const s = getOpenFreehandIJK(e, activeViewport, seriesImageIds);
          if (s) (isNeg ? neg_scribbles : pos_scribbles).push(s);
        }
      }
      //VoxTell - Use provided textPrompts or extract from measurements
      const text_prompts: string[] = textPrompts
        ? (Array.isArray(textPrompts) ? textPrompts : [textPrompts])
        : probe2Labels;

      // Hide measurements after inference unless user has set prompts to always-show
      if (!toolboxState.getPromptsVisible()) {
        currentMeasurements
          .filter(e => e.referenceSeriesUID === currentDisplaySets.SeriesInstanceUID)
          .forEach(e => measurementService.toggleVisibilityMeasurement(e.uid, false));
        dispatchMeasurementStateChanged();
      }

      let url = `/nninteractive/infer/segmentation?image=${currentDisplaySets.SeriesInstanceUID}&output=dicom_seg`;
      let params = {
        largest_cc: false,
      //  device: response.data.trainers.segmentation.config.device,
        result_extension: '.nii.gz',
        result_dtype: 'uint16',
        result_compress: false,
        studyInstanceUID: currentDisplaySets.StudyInstanceUID,
        restore_label_idx: false,
        pos_points: pos_points,
        neg_points: neg_points,
        pos_boxes: pos_boxes,
        neg_boxes: neg_boxes,
        pos_lassos: pos_lassos,
        neg_lassos: neg_lassos,
        pos_scribbles: pos_scribbles,
        neg_scribbles: neg_scribbles,
        texts: text_prompts,
        nninter: true,
        nninter_reset_first: _needsReset,
      };

      let data = constructInferenceFormData(params, null);


      const beforePost = Date.now();
      console.log(`Before Post request: ${(beforePost - start)/1000} Seconds`);
      // Create the axios promise
      const segmentationPromise = axios.post(url, data, {
        responseType: 'arraybuffer',
        headers: {
          //accept: 'application/json, multipart/form-data',
          accept: 'application/octet-stream',
        },
      });

      // Show notification with promise support
      uiNotificationService.show({
        title: 'nnInteractive',
        message: 'Processing nninter segmentation...',
        type: 'info',
        promise: segmentationPromise,
        promiseMessages: {
          loading: 'Processing nninter segmentation...',
          success: () => 'Run Segmentation - Successful',
          error: (error) => `Run Segmentation - Failed: ${error.message || 'Unknown error'}`,
        },
      });

      try {
        // Process the response
        const response = await segmentationPromise;
        console.debug(response);
        if (response.status === 200) {
            const afterPost = Date.now();
            const networkRoundTripMs = afterPost - beforePost;
            const ct = response.headers["content-type"] as string;
            const { meta, seg } = await parseMultipart(response.data, ct);
            const afterParse = Date.now();

            // --- server-side timing breakdown ---
            const sRequestTs     = metaNum(meta as Record<string,unknown>, 'server_request_ts');
            const sBeginTs       = metaNum(meta as Record<string,unknown>, 'server_begin_ts');
            const sEndTs         = metaNum(meta as Record<string,unknown>, 'server_end_ts');
            const sLoad          = metaNum(meta as Record<string,unknown>, 'server_load_elapsed');
            const sImgConvert    = metaNum(meta as Record<string,unknown>, 'server_img_convert_elapsed');
            const sPromptPrep    = metaNum(meta as Record<string,unknown>, 'server_prompt_prep_elapsed');
            const sModelCore     = metaNum(meta as Record<string,unknown>, 'nninter_core_elapsed');
            const sResult        = metaNum(meta as Record<string,unknown>, 'server_result_elapsed');
            const sTotal         = metaNum(meta as Record<string,unknown>, 'nninter_elapsed');
            const sFirstTs       = metaNum(meta as Record<string,unknown>, 'nninter_first_interaction_ts');

            // Four-leg split (all server timestamps share the same host clock as the container):
            //   leg1: POST in flight          = server_request_ts - beforePost (client clock vs server clock; same host → accurate)
            //   leg2: nnInteractive pre-processing    = server_begin_ts - server_request_ts (DICOM download from Orthanc, entirely server-side)
            //   leg3: our infer()             = server_end_ts - server_begin_ts (same clock, exact)
            //   leg4: response in flight      = afterPost - server_end_ts (same host → accurate)
            const postInFlightMs    = (sRequestTs != null) ? sRequestTs * 1000 - beforePost                     : undefined;
            const nninteractivePrepMs       = (sRequestTs != null && sBeginTs != null) ? (sBeginTs - sRequestTs) * 1000 : undefined;
            const serverProcessMs   = (sBeginTs   != null && sEndTs   != null) ? (sEndTs   - sBeginTs)   * 1000 : undefined;
            const responseInFlightMs= (sEndTs     != null)                     ? afterPost - sEndTs * 1000      : undefined;

            console.log(
              `[nninter timing]\n` +
              `  client → nninter():              ${((beforePost - start)/1000).toFixed(3)}s\n` +
              `  ── round-trip total:              ${(networkRoundTripMs/1000).toFixed(3)}s\n` +
              (postInFlightMs     != null ? `     POST in flight:               ${(postInFlightMs/1000).toFixed(3)}s\n` : '') +
              (nninteractivePrepMs        != null ? `     nnInteractive pre-processing:          ${(nninteractivePrepMs/1000).toFixed(3)}s  (Orthanc DICOM download)\n` : '') +
              (serverProcessMs    != null ? `     server processing (infer):     ${(serverProcessMs/1000).toFixed(3)}s\n` : '') +
              (sLoad        != null ? `       ↳ DICOM load:                ${sLoad.toFixed(3)}s\n` : '') +
              (sImgConvert  != null ? `       ↳ img→numpy:                 ${sImgConvert.toFixed(3)}s\n` : '') +
              (sPromptPrep  != null ? `       ↳ prompt prep:               ${sPromptPrep.toFixed(3)}s\n` : '') +
              (sModelCore   != null ? `       ↳ model forward:             ${sModelCore.toFixed(3)}s\n` : '') +
              (sResult      != null ? `       ↳ result retrieve:           ${sResult.toFixed(3)}s\n` : '') +
              (responseInFlightMs != null ? `     response in flight:            ${(responseInFlightMs/1000).toFixed(3)}s\n` : '') +
              `  client parse multipart:          ${((afterParse - afterPost)/1000).toFixed(3)}s`
            );

            const flipped = meta.flipped.toLowerCase() === "true"
            const nninter_elapsed = meta.nninter_elapsed
            const prompt_info = meta.prompt_info
            const label_name = meta.label_name
            const raw = seg

            // Parse crop geometry. The slice loops write directly from cropBytes into
            // each slice's scalar data buffer — no full-volume reconstruction needed.
            // Avoiding the 182 MB allocation eliminates GC pauses that caused 0.3-1.3s jitter.
            const cropBytes = new Uint8Array(raw);
            const predOffset: number[] = JSON.parse((meta as any).pred_offset   || '[0,0,0]');
            const predFull:   number[] = JSON.parse((meta as any).pred_full_shape || '[]');
            const predCrop:   number[] = JSON.parse((meta as any).pred_crop_shape || '[]');

            // Crop geometry (exposed to slice loops below)
            let _segZ0 = 0, _segZ1 = Number.MAX_SAFE_INTEGER;
            let _cropY = 0, _cropX = 0, _y0 = 0, _x0 = 0, _fullX = 0;
            let _hasCropGeom = false;
            if (predFull.length === 3 && predCrop.length === 3) {
              const [, , fullX] = predFull;
              const [cropZ, cropY, cropX] = predCrop;
              const [z0, y0, x0] = predOffset;
              _segZ0 = z0;  _segZ1 = z0 + cropZ;
              _cropY = cropY; _cropX = cropX;
              _y0 = y0; _x0 = x0; _fullX = fullX;
              _hasCropGeom = true;
            } else {
            }
            // Legacy fallback: reconstruct full-volume buffer when crop geometry is unavailable.
            // This path should never trigger for current server builds.
            let new_arrayBuffer: Uint8Array | null = null;
            if (!_hasCropGeom) {
              new_arrayBuffer = cropBytes;
            }

            const imageIds = currentDisplaySets.imageIds;
            let fullImageIds: string[] = []; // the segmentation's full labelmap imageIds after this op


          let merged_derivedImages = [];
          let z_range = [];
          // Per-object model: each object is its OWN segmentation, a single S-image labelmap holding
          // value 1. A new object → fresh S images; a refine → clear this object's map (all nonzero)
          // and rewrite. No blocks.
          if (mode !== 'refine') {
            // ── New object: fresh S-image labelmap, write the crop into it ──
            const _tCreate2 = Date.now();
            let derivedImages_new = await imageLoader.createAndCacheDerivedLabelmapImages(imageIds);
            console.log(`[nninter] createAndCache: ${((Date.now()-_tCreate2)/1000).toFixed(3)}s (${imageIds.length} slices)`);

            if (flipped) derivedImages_new.reverse();
            const _tWrite2 = Date.now();
            for (let i = 0; i < derivedImages_new.length; i++) {
              if (_hasCropGeom && (i < _segZ0 || i >= _segZ1)) continue;
              const voxelManager = derivedImages_new[i].voxelManager as csTypes.IVoxelManager<number>;
              if (_hasCropGeom && i >= _segZ0 && i < _segZ1) {
                const scalarData = voxelManager.getScalarData();
                const c = i - _segZ0;
                const cropSliceBase = c * _cropY * _cropX;
                let wrote = false;
                for (let cy = 0; cy < _cropY; cy++) {
                  const srcRow = cropSliceBase + cy * _cropX;
                  const dstRow = (_y0 + cy) * _fullX + _x0;
                  for (let cx = 0; cx < _cropX; cx++) {
                    if (cropBytes[srcRow + cx] === 1) {
                      scalarData[dstRow + cx] = segmentNumber;
                      wrote = true;
                    }
                  }
                }
                if (wrote) z_range.push(flipped ? derivedImages_new.length - i - 1 : i);
              } else if (!_hasCropGeom && new_arrayBuffer) {
                // Legacy: full-slice scan
                const scalarData = voxelManager.getScalarData();
                const sliceLen = scalarData.length;
                const sliceData = new_arrayBuffer.subarray(i * sliceLen, (i + 1) * sliceLen);
                if (sliceData.some(v => v === 1)){
                  for (let j = 0; j < sliceLen; j++) { if (sliceData[j] === 1) scalarData[j] = segmentNumber; }
                  z_range.push(flipped ? derivedImages_new.length - i - 1 : i);
                }
              }
            }
            if (flipped) derivedImages_new.reverse();
            console.log(`[nninter] pixel write (first): ${((Date.now()-_tWrite2)/1000).toFixed(3)}s`);
            merged_derivedImages = derivedImages_new;
            fullImageIds = derivedImages_new.map((im: any) => im.imageId);
          } else {
            // ── Refine: this object's whole labelmap (single S-image map), clear + rewrite ──
            const _tCacheGet = Date.now();
            merged_derivedImages = priorImageIds.map(imageId => cache.getImage(imageId));
            fullImageIds = priorImageIds;
            console.log(
              `[nninter] refine object ${segmentationId}: ` +
              `map=${merged_derivedImages.length}/${priorImageIds.length} (${((Date.now()-_tCacheGet)/1000).toFixed(3)}s)`
            );
            if (flipped) merged_derivedImages.reverse();

            // ── Pass 1: Clear this object's old pixels ───────────────────────
            // dirtySlices (exact indices) fast path; else bounding-box range scan.
            const _prevDirtySlices = (existingSegments[segmentNumber] as any)
              ?.cachedStats?.dirtySlices as number[] | undefined;
            const _tClear = Date.now();

            const _prevCachedStats = (existingSegments[segmentNumber] as any)?.cachedStats;
            const _hasPrevData = _prevDirtySlices?.length ||
              _prevCachedStats?.segZ0 != null || _prevCachedStats?.segZ1 != null;

            if (_prevDirtySlices?.length) {
              for (const origIdx of _prevDirtySlices) {
                const arrIdx = flipped ? (merged_derivedImages.length - 1 - origIdx) : origIdx;
                const vm = merged_derivedImages[arrIdx]?.voxelManager as csTypes.IVoxelManager<number>;
                if (!vm) continue;
                const sd = vm.getScalarData();
                for (let j = 0; j < sd.length; j++) {
                  if (sd[j] !== 0) sd[j] = 0;
                }
              }
              console.log(`[nninter] clear (${_prevDirtySlices.length} dirty slices): ${((Date.now()-_tClear)/1000).toFixed(3)}s`);
            } else if (_hasPrevData) {
              const _prevZ0: number = (_hasCropGeom && _prevCachedStats?.segZ0 != null)
                ? _prevCachedStats.segZ0 as number : 0;
              const _prevZ1: number = (_hasCropGeom && _prevCachedStats?.segZ1 != null)
                ? _prevCachedStats.segZ1 as number : merged_derivedImages.length;
              const scanZ0 = _hasCropGeom ? Math.min(_prevZ0, _segZ0) : 0;
              const scanZ1 = _hasCropGeom ? Math.max(_prevZ1, _segZ1) : merged_derivedImages.length;
              for (let i = scanZ0; i < scanZ1; i++) {
                const sd = (merged_derivedImages[i].voxelManager as csTypes.IVoxelManager<number>).getScalarData();
                for (let j = 0; j < sd.length; j++) {
                  if (sd[j] !== 0) sd[j] = 0;
                }
              }
              console.log(`[nninter] clear fallback (${scanZ1-scanZ0} slices): ${((Date.now()-_tClear)/1000).toFixed(3)}s`);
            } else {
              console.log(`[nninter] clear skipped (no prior data)`);
            }

            // ── Pass 2: Write new pixels from crop only (no background guard) ──
            const _tWrite3 = Date.now();
            if (_hasCropGeom) {
              for (let i = _segZ0; i < _segZ1; i++) {
                const scalarData = (merged_derivedImages[i].voxelManager as csTypes.IVoxelManager<number>).getScalarData();
                const c = i - _segZ0;
                const cropSliceBase = c * _cropY * _cropX;
                let wrote = false;
                for (let cy = 0; cy < _cropY; cy++) {
                  const srcRow = cropSliceBase + cy * _cropX;
                  const dstRow = (_y0 + cy) * _fullX + _x0;
                  for (let cx = 0; cx < _cropX; cx++) {
                    if (cropBytes[srcRow + cx] === 1) {
                      scalarData[dstRow + cx] = segmentNumber;
                      wrote = true;
                    }
                  }
                }
                if (wrote) z_range.push(flipped ? merged_derivedImages.length - i - 1 : i);
              }
            } else if (new_arrayBuffer) {
              for (let i = 0; i < merged_derivedImages.length; i++) {
                const sd = (merged_derivedImages[i].voxelManager as csTypes.IVoxelManager<number>).getScalarData();
                const sliceData = new_arrayBuffer.subarray(i * sd.length, (i + 1) * sd.length);
                if (sliceData.some(v => v === 1)){
                  for (let j = 0; j < sd.length; j++) { if (sliceData[j] === 1) sd[j] = segmentNumber; }
                  z_range.push(flipped ? merged_derivedImages.length - i - 1 : i);
                }
              }
            }
            console.log(`[nninter] write (${z_range.length} slices): ${((Date.now()-_tWrite3)/1000).toFixed(3)}s`);

            if (flipped) merged_derivedImages.reverse();
          }


          const derivedImageIds = fullImageIds;
          const _uniqImgs = new Set(fullImageIds).size;
          console.log(
            `[nninter/dbg] write done: mode=${mode} object=${segmentationId} full=${fullImageIds.length} ` +
            `unique=${_uniqImgs} map=${merged_derivedImages.length} zSlices=${z_range.length}` +
            (_uniqImgs !== fullImageIds.length
              ? ' ⚠ DUPLICATE imageIds — createAndCacheDerivedLabelmapImages returned aliased ids!'
              : '')
          );
          const objectColor =
            ((existingSegments[segmentNumber] as any)?.cachedStats?.color as number[] | undefined) ||
            objectColorForOrdinal(_objectOrdinal);
          segments[segmentNumber] = {
            segmentIndex: segmentNumber,
            color: objectColor,
            // Keep a pre-existing (or user-renamed) label; name a brand-new object "Object N"
            // (each object is its own segmentation, so the index is always 1 and unhelpful).
            label: existingSegments[segmentNumber]?.label || `Object ${_objectOrdinal ?? 1}`,
            locked: false,
            active: false,
            cachedStats: {
              modifiedTime: utils.formatDate(Date.now(), 'YYYYMMDD'),
              algorithmType: 'SEMIAUTOMATIC',
              algorithmName: currentDisplaySets.SeriesInstanceUID,
              description: prompt_info + " (nninter " + nninter_elapsed + "s)",
              center:  z_range.length > 0 ? z_range.reduce((sum, z) => sum + z, 0) / z_range.length : 0,
              // z-range kept for fallback; dirtySlices is the fast-path clear target
              segZ0: _hasCropGeom ? _segZ0 : 0,
              segZ1: _hasCropGeom ? _segZ1 : (merged_derivedImages?.length ?? 0),
              dirtySlices: z_range,
              color: objectColor,
            }
          } as any;
          console.log(`Before add or update segs: ${(Date.now() - start)/1000} Seconds`);
          // Post-segmentation processing: update representations, handle viewports, trigger events
          await postSegmentationProcessing({
            activeViewportId,
            segmentationId,
            segmentNumber,
            segments,
            derivedImageIds,
            currentDisplaySets,
            imageIds,
            existingSegments,
            existing,
            mode,
            activeSegmentation,
            currentImageIdIndex,
            z_range,
          });
          // The backend now holds THIS segment's interactions (reset_first applied if we switched).
          _serverObjectId = serverObjKey(segmentationId, segmentNumber);
          const tViz = Date.now();
          console.log(
            `[nninter timing]\n` +
            `  OHIF post-processing:         ${((tViz - afterParse)/1000).toFixed(3)}s  (parse→visible)\n` +
            `  total client time:            ${((tViz - start)/1000).toFixed(3)}s`
          );
          return response;
        }
      } catch (error) {
        if (_isSessionExpiredError(error)) {
          toolboxState.setSessionActive(false);
          uiNotificationService?.show({
            title: 'nnInteractive',
            message: 'Session expired — please Initialize again.',
            type: 'warning',
          });
        }
        console.error('Nninter segmentation error:', error);
        throw error;
      }
    },

    jumpToSegment: () => {
      const activeViewportId = viewportGridService.getState().activeViewportId;
      const segmentationService = servicesManager.services.segmentationService;
      const activeSegmentation = segmentationService.getActiveSegmentation(activeViewportId);
      if (activeSegmentation != undefined) {
        segmentationService.jumpToSegmentCenter(activeSegmentation.segmentationId, 1, activeViewportId)
      }
    },
    toggleCurrentSegment: () => {
      const activeViewportId = viewportGridService.getState().activeViewportId;
      const segmentationService = servicesManager.services.segmentationService;
      const activeSegmentation = segmentationService.getActiveSegmentation(activeViewportId);
      if (activeSegmentation != undefined) {
        segmentationService.toggleSegmentationRepresentationVisibility(activeViewportId, {
          segmentationId: activeSegmentation.segmentationId,
          type: csToolsEnums.SegmentationRepresentations.Labelmap
        });
      }
    },
  };

  const commandNames = [
    'setAiToolActive',
    'runAiSegmentation',
    'initNninter',
    'nninterSessionStatus',
    'closeNninterSession',
    'undoNninter',
    'resetNninter',
    'resetSegment',
    'loadSegmentForRefinement',
    'armNextNninterObject',
    'nninter',
    'jumpToSegment',
    'toggleCurrentSegment',
  ];

  const definitions: Record<string, any> = commandNames.reduce((commandDefinitions, commandName) => {
    const commandFn = actions[commandName];
    if (typeof commandFn !== 'function') {
      throw new Error(`Missing nnInteractive command action: ${commandName}`);
    }

    commandDefinitions[commandName] = { commandFn };
    return commandDefinitions;
  }, {});

  Object.assign(definitions, {
    runSegmentBidirectional: {
      commandFn: actions.runSegmentBidirectional,
      context: 'CORNERSTONE',
    },
    updateStoredSegmentationPresentation: {
      commandFn: actions.updateStoredSegmentationPresentation,
      context: 'CORNERSTONE',
    },
    toggleToolActiveToolbar: {
      commandFn: actions.toggleToolActiveToolbar,
      context: 'CORNERSTONE',
    },
    toggleSegmentMeasurement: {
      commandFn: actions.toggleSegmentMeasurement,
      context: 'CORNERSTONE',
    },
    getSegmentMeasurementVisibility: {
      commandFn: actions.getSegmentMeasurementVisibility,
      context: 'CORNERSTONE',
    },
    toggleSegmentationVisibilityAllViewports: {
      commandFn: actions.toggleSegmentationVisibilityAllViewports,
      context: 'CORNERSTONE',
    },
    removeSegmentationFromViewport: {
      commandFn: actions.removeSegmentationFromViewport,
      context: 'CORNERSTONE',
    },
    generateSegmentation: {
      commandFn: actions.generateSegmentation,
      context: 'SEGMENTATION',
    },
    downloadSegmentation: {
      commandFn: actions.downloadSegmentation,
      context: 'SEGMENTATION',
    },
    storeSegmentation: {
      commandFn: actions.storeSegmentation,
      context: 'SEGMENTATION',
    },
    downloadNninterSegmentation: {
      commandFn: actions.downloadNninterSegmentation,
      context: 'SEGMENTATION',
    },
    storeNninterSegmentation: {
      commandFn: actions.storeNninterSegmentation,
      context: 'SEGMENTATION',
    },
  });

  return {
    actions,
    definitions,
    defaultContext: 'DEFAULT',
  };
};

export default commandsModule;
