import dcmjs from 'dcmjs';
import { DicomMetadataStore, utils, Types } from '@ohif/core';
import {
  Enums as csToolsEnums,
  Types as cstTypes,
  segmentation as csToolsSegmentation,
} from '@cornerstonejs/tools';
import * as cornerstoneTools from '@cornerstonejs/tools';
import { updateLabelmapSegmentationImageReferences } from '@cornerstonejs/tools/segmentation/updateLabelmapSegmentationImageReferences';
import {
  cache,
  imageLoader,
  metaData,
  Types as csTypes,
  utilities as csUtils,
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

function pointInPolygon(x: number, y: number, polygon: number[][]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0];
    const yi = polygon[i][1];
    const xj = polygon[j][0];
    const yj = polygon[j][1];
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi || 1) + xi;
    if (intersects) {
      inside = !inside;
    }
  }
  return inside;
}

function getImageWidth(image: any, displaySet: any, sliceIndex: number): number {
  return (
    image?.columns ||
    image?.width ||
    displaySet?.instances?.[sliceIndex]?.Columns ||
    displaySet?.images?.[sliceIndex]?.Columns ||
    0
  );
}

function getClosedFreehandBoundaryIJK(measurement: any, viewport: any): number[][] | undefined {
  const dataValues = Object.values(measurement?.data ?? {});
  const cachedBoundary = dataValues.find((value: any) => value?.boundary?.length)?.boundary;
  if (cachedBoundary?.length) {
    return cachedBoundary.map((point: number[]) => point.map(value => Math.round(value)));
  }

  const worldPoints =
    measurement?.points ??
    measurement?.data?.contour?.polyline ??
    dataValues.find((value: any) => value?.points?.length)?.points ??
    dataValues.find((value: any) => value?.polyline?.length)?.polyline;

  if (!worldPoints?.length) {
    return undefined;
  }

  const imageData = viewport?.getImageData?.()?.imageData ?? viewport?.getImageData?.();
  if (!imageData || !csUtils.transformWorldToIndex) {
    return undefined;
  }

  const viewportImageIds = viewport?.getImageIds?.() ?? [];
  const referencedSliceIndex = viewportImageIds.indexOf(measurement?.referencedImageId);

  return worldPoints
    .map((point: number[]) => csUtils.transformWorldToIndex(imageData, point))
    .filter((point: number[]) => point?.length >= 3 && point.every(Number.isFinite))
    .map((point: number[]) => [
      Math.round(point[0]),
      Math.round(point[1]),
      referencedSliceIndex >= 0 ? referencedSliceIndex : Math.round(point[2]),
    ]);
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

function worldToIJKForMeasurement(point: number[], measurement: any, viewport: any): number[] | undefined {
  const imageData = viewport?.getImageData?.()?.imageData ?? viewport?.getImageData?.();
  if (!imageData || !csUtils.transformWorldToIndex) {
    return;
  }

  const ijk = csUtils.transformWorldToIndex(imageData, point);
  if (!ijk?.length || !ijk.every(Number.isFinite)) {
    return;
  }

  const viewportImageIds = viewport?.getImageIds?.() ?? [];
  const referencedSliceIndex = viewportImageIds.indexOf(measurement?.referencedImageId);

  return [
    Math.round(ijk[0]),
    Math.round(ijk[1]),
    referencedSliceIndex >= 0 ? referencedSliceIndex : Math.round(ijk[2]),
  ];
}

function getPromptPointIJK(measurement: any, viewport: any): number[] | undefined {
  const cachedIndex = Object.values(measurement?.data ?? {}).find(
    (value: any) => value?.index?.length === 3
  ) as any;
  if (cachedIndex?.index?.length === 3) {
    return cachedIndex.index.map((value: number) => Math.round(value));
  }

  const [worldPoint] = getMeasurementWorldPoints(measurement);
  return worldPoint ? worldToIJKForMeasurement(worldPoint, measurement, viewport) : undefined;
}

function getRectangleBoxIJK(measurement: any, viewport: any): number[][] | undefined {
  const cachedPoints = Object.values(measurement?.data ?? {}).find(
    (value: any) => value?.pointsInShape?.length
  ) as any;
  if (cachedPoints?.pointsInShape?.length) {
    return [cachedPoints.pointsInShape.at(0).pointIJK, cachedPoints.pointsInShape.at(-1).pointIJK];
  }

  const ijkPoints = getMeasurementWorldPoints(measurement)
    .map(point => worldToIJKForMeasurement(point, measurement, viewport))
    .filter(Boolean) as number[][];

  if (ijkPoints.length === 0) {
    return;
  }

  const xValues = ijkPoints.map(point => point[0]);
  const yValues = ijkPoints.map(point => point[1]);
  const z = ijkPoints[0][2];

  return [
    [Math.min(...xValues), Math.min(...yValues), z],
    [Math.max(...xValues), Math.max(...yValues), z],
  ];
}

function getOpenFreehandIJK(measurement: any, viewport: any): number[][] | undefined {
  const cachedScribble = Object.values(measurement?.data ?? {}).find(
    (value: any) => value?.scribble?.length
  ) as any;
  if (cachedScribble?.scribble?.length) {
    return cachedScribble.scribble.map((point: number[]) => point.map(value => Math.round(value)));
  }

  const ijkPoints = getMeasurementWorldPoints(measurement)
    .map(point => worldToIJKForMeasurement(point, measurement, viewport))
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

  /**
   * Helper function to handle post-segmentation processing after segmentation data is created/updated.
   * This includes updating representations, handling viewports, and triggering events.
   */
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
    activeSegmentation: any;
    currentImageIdIndex?: number;
    z_range: number[];
  }) {
    // Get the representations for the segmentation to recover the visibility of the segments
    const representations = servicesManager.services.segmentationService.getSegmentationRepresentations(activeViewportId, { segmentationId });

    if (segmentNumber === 1 && Object.keys(existingSegments).length === 0 && !existing) {
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
              center: z_range.length > 0 ? z_range.reduce((sum, z) => sum + z, 0) / z_range.length : 0
            },
            label: currentDisplaySets.SeriesDescription,
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

    servicesManager.services.segmentationService.setActiveSegment(segmentationId, segmentNumber);
    toolboxState.setCurrentActiveSegment(segmentNumber);

    if (toolboxState.getRefineNew()) {
      toolboxState.setRefineNew(false);
    }

    if (!existing) {
      // ── First-ever inference: no actors exist yet, must do full viewport setup ──

      // Recover the visibility of any pre-existing segments
      for (let i = 0; i < representations.length; i++) {
        const representation = representations[i];
        const segs = Object.values(representation.segments);
        for (let j = 0; j < segs.length; j++) {
          const seg = segs[j];
          servicesManager.services.segmentationService.setSegmentVisibility(activeViewportId, representation.segmentationId, (seg as any).segmentIndex, (seg as any).visible);
        }
      }

      // Add representations for all viewports
      const currentViewportIds = servicesManager.services.cornerstoneViewportService.getViewportIds();
      const regularViewportIds: string[] = [];
      const volume3DViewportIds: string[] = [];
      for (const viewportId of currentViewportIds) {
        const vp = servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(viewportId);
        if (vp instanceof VolumeViewport3D) volume3DViewportIds.push(viewportId);
        else regularViewportIds.push(viewportId);
      }

      for (const viewportId of currentViewportIds) {
        servicesManager.services.segmentationService.removeSegmentationRepresentations(viewportId, { segmentationId });
      }
      await Promise.all(regularViewportIds.map(viewportId =>
        servicesManager.services.segmentationService.addSegmentationRepresentation(viewportId, { segmentationId })
      ));
      for (const viewportId of volume3DViewportIds) {
        const vp = servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(viewportId);
        updateLabelmapSegmentationImageReferences(viewportId, segmentationId);
        await servicesManager.services.segmentationService.addSegmentationRepresentation(viewportId, {
          segmentationId,
          type: csToolsEnums.SegmentationRepresentations.Labelmap,
        });
        await new Promise(resolve => setTimeout(resolve, 100));
        requestAnimationFrame(() => vp?.render());
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
      // VTK actors for all viewports already exist and reference the same image
      // buffers that were updated by the voxel-writing loop above.
      // labelmapDisplay._setLabelmapColorAndOpacity now calls
      // scalars.modified() + inputData.modified() unconditionally, so the GPU
      // texture is re-uploaded on the next rAF render triggered by the event.
      // No remove/re-add or scroll needed — saves ~300–350 ms per inference.
      eventTarget.dispatchEvent(
        new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
          detail: { segmentationId },
        })
      );
    }
  }


  const actions = {
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
      const segmentation = csToolsSegmentation.state.getSegmentation(segmentationId);
      const { imageIds } = segmentation.representationData.Labelmap;
      const segImages = imageIds.map(imageId => cache.getImage(imageId));
      const referencedImageIds = segImages.map(image => image?.referencedImageId);

      await Promise.all(
        referencedImageIds.map(referencedImageId => {
          if (!referencedImageId || cache.getImage(referencedImageId)) {
            return Promise.resolve();
          }
          return imageLoader.loadAndCacheImage(referencedImageId).catch(error => {
            console.warn(`Failed to load referenced image ${referencedImageId}:`, error);
          });
        })
      );

      const referencedImages = segImages.map(image =>
        image?.referencedImageId ? cache.getImage(image.referencedImageId) : null
      );
      const labelmaps2D = [];

      let z = 0;
      for (const segImage of segImages) {
        const segmentsOnLabelmap = new Set();
        const pixelData = segImage.getPixelData();
        const { rows, columns } = segImage;

        for (let i = 0; i < pixelData.length; i++) {
          const segment = pixelData[i];
          if (segment !== 0) {
            segmentsOnLabelmap.add(segment);
          }
        }

        labelmaps2D[z++] = {
          segmentsOnLabelmap: Array.from(segmentsOnLabelmap),
          pixelData,
          rows,
          columns,
        };
      }

      const allSegmentsOnLabelmap = labelmaps2D.map(labelmap => labelmap.segmentsOnLabelmap);
      const labelmap3D = {
        segmentsOnLabelmap: Array.from(new Set(allSegmentsOnLabelmap.flat())),
        metadata: [],
        labelmaps2D,
      };
      const segmentationInOHIF = segmentationService.getSegmentation(segmentationId);
      const representations = segmentationService.getRepresentationsForSegmentation(segmentationId);

      Object.entries(segmentationInOHIF.segments).forEach(([segmentIndex, segment]: [string, any]) => {
        if (!segment) {
          return;
        }

        const firstRepresentation = representations[0];
        const color = segmentationService.getSegmentColor(
          firstRepresentation.viewportId,
          segmentationId,
          segment.segmentIndex
        );
        const RecommendedDisplayCIELabValue = dcmjs.data.Colors.rgb2DICOMLAB(
          color.slice(0, 3).map(value => value / 255)
        ).map(value => Math.round(value));

        let segmentMetadata: any = {};
        if (segmentation.cachedStats.data !== undefined && segmentation.cachedStats.data.length > 1) {
          segmentMetadata = segmentation.cachedStats.data
            .filter(e => e !== undefined && e !== null)
            .find(e => e.SegmentNumber == segmentIndex);
          if (segmentMetadata !== undefined && Object.keys(segmentMetadata).length !== 0) {
            segmentMetadata.SegmentNumber = segmentIndex.toString();
            segmentMetadata.SegmentLabel = segment.label;
            segmentMetadata.RecommendedDisplayCIELabValue = RecommendedDisplayCIELabValue;
            segmentMetadata.SegmentAlgorithmType = 'SEMIAUTOMATIC';
          }
        }

        if (segmentMetadata === undefined || Object.keys(segmentMetadata).length === 0) {
          segmentMetadata = {
            SegmentNumber: segmentIndex.toString(),
            SegmentLabel: segment.label,
            SegmentAlgorithmType: segment?.algorithmType || 'MANUAL',
            SegmentAlgorithmName: segment?.algorithmName || 'OHIF Brush',
            RecommendedDisplayCIELabValue,
            SegmentedPropertyCategoryCodeSequence: {
              CodeValue: 'T-D0050',
              CodingSchemeDesignator: 'SRT',
              CodeMeaning: 'Tissue',
            },
            SegmentedPropertyTypeCodeSequence: {
              CodeValue: 'T-D0050',
              CodingSchemeDesignator: 'SRT',
              CodeMeaning: 'Tissue',
            },
          };
        }

        if (segment.cachedStats?.description !== undefined) {
          segmentMetadata.SegmentDescription = segment.cachedStats.description;
        }
        if (segment.cachedStats?.algorithmName !== undefined) {
          segmentMetadata.SegmentAlgorithmName = segment.cachedStats.algorithmName;
        }
        if (segment.cachedStats?.algorithmType !== undefined) {
          segmentMetadata.SegmentAlgorithmType = ['AUTOMATIC', 'SEMIAUTOMATIC', 'MANUAL'].includes(
            segment.cachedStats.algorithmType
          )
            ? segment.cachedStats.algorithmType
            : 'SEMIAUTOMATIC';
        }
        if (segmentation.cachedStats.seriesInstanceUid !== undefined) {
          segmentMetadata.SegmentAlgorithmName = segmentation.cachedStats.seriesInstanceUid;
        }

        labelmap3D.metadata[segmentIndex] = segmentMetadata;
      });

      return generateSEGFromLabelmap(referencedImages, labelmap3D, metaData, options);
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
      const initPromise = axios.post(url, data, {
        responseType: 'arraybuffer',
        headers: {
          accept: 'application/json, multipart/form-data',
        },
      }).catch(recoverInitializedSession);

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

        let merged = segImageIds.map(imageId => cache.getImage(imageId));
        if (flipped) merged.reverse();

        // Pass 1: clear all voxels of the active segment (use dirtySlices when available).
        const prevStats = (activeSegmentation.segments?.[segmentNumber] as any)?.cachedStats;
        const prevDirty: number[] | undefined = prevStats?.dirtySlices;
        const clearSlice = (arrIdx: number) => {
          const vm = merged[arrIdx]?.voxelManager;
          if (!vm) return;
          const sd = vm.getScalarData();
          for (let j = 0; j < sd.length; j++) {
            if (sd[j] === segmentNumber) sd[j] = 0;
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
    async applyNninterManualCorrection() {
      if (toolboxState.getLocked()) {
        return;
      }

      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);
      const displaySetInstanceUID = activeViewportSpecificData?.displaySetInstanceUIDs?.[0];
      const currentDisplaySets = displaySetService.activeDisplaySets.find(
        e => e.displaySetInstanceUID === displaySetInstanceUID
      );
      if (!currentDisplaySets) {
        return;
      }

      const activeSegmentation =
        servicesManager.services.segmentationService.getActiveSegmentation(activeViewportId);
      const activeSegment = servicesManager.services.segmentationService.getActiveSegment(activeViewportId);
      const segmentationId = activeSegmentation?.segmentationId;
      const segmentNumber = activeSegment?.segmentIndex;
      const labelmapImageIds: string[] =
        (activeSegmentation?.representationData?.Labelmap as any)?.imageIds ?? [];

      if (!segmentationId || segmentNumber == null || labelmapImageIds.length === 0) {
        uiNotificationService.show({
          title: 'Manual correction',
          message: 'Select an nnInteractive segment before applying manual corrections.',
          type: 'warning',
          duration: 4000,
        });
        return;
      }

      const images = await Promise.all(
        labelmapImageIds.map(async imageId => {
          const cachedImage = cache.getImage(imageId);
          if (cachedImage) {
            return cachedImage;
          }

          try {
            return await imageLoader.loadAndCacheImage(imageId);
          } catch {
            return undefined;
          }
        })
      );
      const firstImage = images.find(Boolean);
      if (!firstImage) {
        return;
      }
      const activeViewport =
        servicesManager.services.cornerstoneViewportService.getCornerstoneViewport(activeViewportId);

      const dirtySlices = new Set<number>();
      const correctionMeasurements = measurementService.getMeasurements().filter((measurement: any) => {
        return (
          measurement.referenceSeriesUID === currentDisplaySets.SeriesInstanceUID &&
          measurement.toolName === 'PlanarFreehandROI3' &&
          measurement.metadata?.manualCorrection === true &&
          (measurement.metadata?.SegmentNumber == null ||
            measurement.metadata?.SegmentNumber === segmentNumber)
        );
      });
      let usableCorrectionCount = 0;
      let changedPixelCount = 0;

      for (const measurement of correctionMeasurements) {
        const boundary = getClosedFreehandBoundaryIJK(measurement, activeViewport);
        if (!boundary?.length) {
          continue;
        }
        const sliceIndex = Math.round(boundary[0][2]);
        const image = images[sliceIndex];
        const voxelManager = image?.voxelManager as csTypes.IVoxelManager<number>;
        if (!voxelManager) {
          continue;
        }
        const scalarData = voxelManager.getScalarData();
        const width = getImageWidth(image, currentDisplaySets, sliceIndex);
        if (!width) {
          continue;
        }
        usableCorrectionCount += 1;
        const height = Math.floor(scalarData.length / width);
        const xValues = boundary.map(point => Math.round(point[0]));
        const yValues = boundary.map(point => Math.round(point[1]));
        const xMin = Math.max(0, Math.min(...xValues));
        const xMax = Math.min(width - 1, Math.max(...xValues));
        const yMin = Math.max(0, Math.min(...yValues));
        const yMax = Math.min(height - 1, Math.max(...yValues));
        const remove = !!measurement.metadata?.neg;

        for (let y = yMin; y <= yMax; y++) {
          const row = y * width;
          for (let x = xMin; x <= xMax; x++) {
            if (!pointInPolygon(x + 0.5, y + 0.5, boundary)) {
              continue;
            }
            const offset = row + x;
            if (remove) {
              if (scalarData[offset] === segmentNumber) {
                scalarData[offset] = 0;
                changedPixelCount += 1;
              }
            } else {
              if (scalarData[offset] !== segmentNumber) {
                scalarData[offset] = segmentNumber;
                changedPixelCount += 1;
              }
            }
          }
        }
        voxelManager.setScalarData(scalarData);
        dirtySlices.add(sliceIndex);
      }

      if (correctionMeasurements.length > 0 && usableCorrectionCount === 0) {
        uiNotificationService.show({
          title: 'Manual correction',
          message: 'Could not convert the drawn lasso into labelmap pixels.',
          type: 'warning',
          duration: 4000,
        });
        return;
      }
      if (correctionMeasurements.length > 0 && changedPixelCount === 0) {
        uiNotificationService.show({
          title: 'Manual correction',
          message: 'The drawn lasso did not change any labelmap pixels.',
          type: 'warning',
          duration: 4000,
        });
        return;
      }

      const firstScalarData = (firstImage.voxelManager as csTypes.IVoxelManager<number>).getScalarData();
      const maskBytes = new Uint8Array(images.length * firstScalarData.length);
      let cursor = 0;
      for (let sliceIndex = 0; sliceIndex < images.length; sliceIndex++) {
        const image = images[sliceIndex];
        const scalarData = (image?.voxelManager as csTypes.IVoxelManager<number> | undefined)?.getScalarData();
        if (!scalarData) {
          cursor += firstScalarData.length;
          continue;
        }
        let sliceDirty = dirtySlices.has(sliceIndex);
        for (let i = 0; i < scalarData.length; i++) {
          if (scalarData[i] === segmentNumber) {
            maskBytes[cursor + i] = 1;
            sliceDirty = true;
          }
        }
        if (sliceDirty) {
          dirtySlices.add(sliceIndex);
        }
        cursor += scalarData.length;
      }

      const segment = activeSegmentation.segments?.[segmentNumber];
      if (segment) {
        segment.cachedStats = {
          ...(segment.cachedStats ?? {}),
          dirtySlices: Array.from(dirtySlices).sort((a, b) => a - b),
        };
      }

      if (correctionMeasurements.length > 0) {
        measurementService.removeMany(correctionMeasurements.map((measurement: any) => measurement.uid));
      }

      eventTarget.dispatchEvent(
        new CustomEvent(csToolsEnums.Events.SEGMENTATION_DATA_MODIFIED, {
          detail: { segmentationId },
        })
      );
      servicesManager.services.cornerstoneViewportService.getRenderingEngine()?.render();

      const params = {
        studyInstanceUID: currentDisplaySets.StudyInstanceUID,
        nninter: 'set_mask',
        segmentNumber,
      };
      const data = constructInferenceFormData(params, [
        {
          name: 'mask',
          data: new Blob([maskBytes], { type: 'application/octet-stream' }),
          fileName: 'mask.raw',
        },
      ]);

      await axios.post(
        `/nninteractive/infer/segmentation?image=${currentDisplaySets.SeriesInstanceUID}&output=dicom_seg`,
        data,
        {
          responseType: 'arraybuffer',
          headers: { accept: 'application/octet-stream' },
        }
      );

      uiNotificationService.show({
        title: 'Manual correction',
        message: 'Mask synced as nnInteractive baseline.',
        type: 'success',
        duration: 2500,
      });
    },
    async nninter(textPrompts?: string | string[]) {
      if (toolboxState.getLocked()) {
        return;
      }

      const overlap = false;
      const start = Date.now();

      const { activeViewportId, viewports } = viewportGridService.getState();
      const activeViewportSpecificData = viewports.get(activeViewportId);

      const currentImageIdIndex = servicesManager.services.cornerstoneViewportService
        .getCornerstoneViewport(activeViewportId)
        ?.getCurrentImageIdIndex?.();
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


      const activeSegmentation = servicesManager.services.segmentationService.getActiveSegmentation(activeViewportId)
      let segmentNumber = 1;
      let segments: { [segmentIndex: string]: cstTypes.Segment } = {};
      let segmentationId = `${csUtils.uuidv4()}`
      let _needsReset = false; // set true when switching segments; folded into inference POST
      if (activeSegmentation !== undefined){
        segments = activeSegmentation.segments;
      if (Object.values(segments).length > 0) {
        // Find the minimum available segment number
        const existingSegmentNumbers = Object.values(segments).map(e => e.segmentIndex).sort((a, b) => a - b);
        let minAvailableNumber = 1;
        // Find the first gap in segment numbers, or use the next number after the highest
        for (let i = 0; i < existingSegmentNumbers.length; i++) {
          if (existingSegmentNumbers[i] !== minAvailableNumber) {
            break;
          }
          minAvailableNumber++;
        }
        segmentNumber = minAvailableNumber;
        if (!toolboxState.getRefineNew()) {
          const activeSegment = servicesManager.services.segmentationService.getActiveSegment(activeViewportId);
          if (activeSegment !== undefined){
            for (let i = 0; i < unAssignedMeasurements.length; i++) {
              const e = unAssignedMeasurements[i];
              e.metadata.SegmentNumber = activeSegment.segmentIndex;
              e.metadata.segmentationId = activeSegmentation.segmentationId;
            }
            segmentNumber = activeSegment.segmentIndex;
            _needsReset = toolboxState.getCurrentActiveSegment() !== segmentNumber;
            if (_needsReset) {
              toolboxState.setCurrentActiveSegment(segmentNumber);
            }
          } else {
            uiNotificationService.show({
              title: 'Click Segment to refine',
              message: 'No active segment found, please click segment to refine',
              type: 'warning',
              duration: 4000,
            });
            return
          }
        } else {
          // For new Segment
          for (let i = 0; i < unAssignedMeasurements.length; i++) {
            const e = unAssignedMeasurements[i];
            e.metadata.SegmentNumber = segmentNumber;
            e.metadata.segmentationId = activeSegmentation.segmentationId;
          }
        }
      } else{
        // No existing segments in current active segmentation
        for (let i = 0; i < unAssignedMeasurements.length; i++) {
          const e = unAssignedMeasurements[i];
          e.metadata.SegmentNumber = segmentNumber;
          e.metadata.segmentationId = activeSegmentation.segmentationId;
        }
      }
    } else {
      // No existing segmentation
      for (let i = 0; i < unAssignedMeasurements.length; i++) {
        const e = unAssignedMeasurements[i];
        e.metadata.SegmentNumber = segmentNumber;
        e.metadata.segmentationId = segmentationId;
      }
    }


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
      for (const e of currentMeasurements) {
        if (e.referenceSeriesUID !== seriesUID || e.metadata.SegmentNumber !== segmentNumber) continue;
        const isNeg = !!e.metadata.neg;
        if (e.toolName === 'Probe2') {
          const index = getPromptPointIJK(e, activeViewport);
          if (!index) {
            continue;
          }
          (isNeg ? neg_points : pos_points).push(index);
          if (!isNeg && !textPrompts) probe2Labels.push(e.label);
        } else if (e.toolName === 'RectangleROI2') {
          const box = getRectangleBoxIJK(e, activeViewport);
          if (!box?.length) {
            continue;
          }
          (isNeg ? neg_boxes : pos_boxes).push(box);
        } else if (e.toolName === 'PlanarFreehandROI3') {
          const b = getClosedFreehandBoundaryIJK(e, activeViewport);
          if (b) (isNeg ? neg_lassos : pos_lassos).push(b);
        } else if (e.toolName === 'PlanarFreehandROI2') {
          const s = getOpenFreehandIJK(e, activeViewport);
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

            let imageIds = currentDisplaySets.imageIds



            let existingSegments: { [segmentIndex: string]: cstTypes.Segment } = {};

            let segImageIds = [];

            let existing = false;
            // Find existing segmentation with matching seriesInstanceUid
            if (activeSegmentation !== undefined){
              let existingseriesInstanceUid = activeSegmentation.cachedStats?.seriesInstanceUid;

              if (existingseriesInstanceUid === undefined) {
                const segments = Object.values(activeSegmentation.segments);
                for (let j = 0; j < segments.length; j++) {
                  const segment = segments[j];
                  if (segment.cachedStats?.algorithmName !== undefined) {
                    existingseriesInstanceUid = segment.cachedStats.algorithmName;
                  }
                }
              }

              if (existingseriesInstanceUid === currentDisplaySets.SeriesInstanceUID) {
                existingSegments = activeSegmentation.segments || {};
                segmentationId = activeSegmentation.segmentationId;
                segImageIds = activeSegmentation.representationData.Labelmap.imageIds;
                existing = true;
              }
            }


          let merged_derivedImages = [];
          let z_range = [];
          if(overlap){
          const _tCreate = Date.now();
          let derivedImages_new = await imageLoader.createAndCacheDerivedLabelmapImages(imageIds);
          let derivedImages = [];
          if (segImageIds.length > 0){
            derivedImages = segImageIds.map(imageId => cache.getImage(imageId));
          }

          if(flipped){
            derivedImages_new.reverse();
          }
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
              const sliceData = new_arrayBuffer.slice(i * sliceLen, (i + 1) * sliceLen);
              if (sliceData.some(v => v === 1)) {
                voxelManager.setScalarData(sliceData.map(v => v === 1 ? segmentNumber : v));
                z_range.push(flipped ? derivedImages_new.length - i - 1 : i);
              }
            }
          }
          console.log(`After slice assignment: ${(Date.now() - start)/1000} Seconds`);


          let filteredDerivedImages = [];
          const imgLength = imageIds.length;
          let updatedIndices = new Set<number>();

          // If toolboxState.getRefineNew() is false (Refine), exclude derivedImages that contain segmentNumber
          // Each derivedImage is binary mask of a single slice ([0],[0,1],[0,2],[0,3].. etc)
          // derivedImages size is imgLength * the number of segment
          // We need to filter out the derivedImages block that contain segmentNumber (consists of [0] or [0, segmentNumber] masks)
          // If filter out which contains segmentNumber and all [0] masks, it can lead to incorrect calculation of the segment. e.g. bidirectional measurement
          if (!toolboxState.getRefineNew() && derivedImages.length > 0) {
            let addFlag = true;
            for (let i = 0; i < derivedImages.length; i++) {
              const image = derivedImages[i];
              const voxelManager = image.voxelManager as csTypes.IVoxelManager<number>;
              const scalarData = voxelManager.getScalarData();
              if (scalarData.some(value => value === segmentNumber)) {
                const updatedScalarData = scalarData.map(v => (v === segmentNumber ? 0 : v));
                voxelManager.setScalarData(updatedScalarData);
                if (addFlag) {
                  for (let j = 0; j < imgLength; j++) {
                    updatedIndices.add(Math.floor(i / imgLength) * imgLength + j);
                  }
                  addFlag = false;
                }
              }
            }
            for (let i = 0; i < derivedImages.length; i++) {
              if (!updatedIndices.has(i)) {
                filteredDerivedImages.push(derivedImages[i]);
              }
            }
          } else if (derivedImages.length > 0) {
            filteredDerivedImages = derivedImages;
          }

          merged_derivedImages = [...filteredDerivedImages, ...derivedImages_new]
        } else {
          const _tElse = Date.now();
          if (segImageIds.length == 0){
            const _tCreate2 = Date.now();
            let derivedImages_new = await imageLoader.createAndCacheDerivedLabelmapImages(imageIds);
            console.log(`[nninter] createAndCache: ${((Date.now()-_tCreate2)/1000).toFixed(3)}s (${imageIds.length} slices)`);

            if(flipped){
              derivedImages_new.reverse();
            }
            const _tWrite2 = Date.now();
            for (let i = 0; i < derivedImages_new.length; i++) {
              if (_hasCropGeom && (i < _segZ0 || i >= _segZ1)) continue;
              const voxelManager = derivedImages_new[i]
                .voxelManager as csTypes.IVoxelManager<number>;              // Write directly from cropBytes into the slice's scalar buffer.
              // Iterates only cropY×cropX elements (fits in L2 cache) vs 262K full-slice scan.
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
            if(flipped){
              derivedImages_new.reverse();
            }
            console.log(`[nninter] pixel write (first): ${((Date.now()-_tWrite2)/1000).toFixed(3)}s`);
            merged_derivedImages = derivedImages_new
          } else {
            const _tCacheGet = Date.now();
            merged_derivedImages = segImageIds.map(imageId => cache.getImage(imageId));
            console.log(`[nninter] cache.getImage (refine): ${((Date.now()-_tCacheGet)/1000).toFixed(3)}s`);
            if(flipped){
              merged_derivedImages.reverse();
            }

            // ── Pass 1: Clear old pixels ─────────────────────────────────────
            // Use dirtySlices (exact indices that have pixels) when available.
            // Falls back to the range-based scan on first refinement or old data.
            const _prevDirtySlices = (existingSegments[segmentNumber] as any)
              ?.cachedStats?.dirtySlices as number[] | undefined;
            const _tClear = Date.now();

            const _prevCachedStats = (existingSegments[segmentNumber] as any)?.cachedStats;
            const _hasPrevData = _prevDirtySlices?.length ||
              _prevCachedStats?.segZ0 != null || _prevCachedStats?.segZ1 != null;

            if (_prevDirtySlices?.length) {
              // Fast path: only touch slices that actually contain pixels (~20-50 vs 500+)
              for (const origIdx of _prevDirtySlices) {
                const arrIdx = flipped ? (merged_derivedImages.length - 1 - origIdx) : origIdx;
                const vm = merged_derivedImages[arrIdx]?.voxelManager as csTypes.IVoxelManager<number>;
                if (!vm) continue;
                const sd = vm.getScalarData();
                for (let j = 0; j < sd.length; j++) {
                  if (sd[j] === segmentNumber) sd[j] = 0;
                }
              }
              console.log(`[nninter] clear (${_prevDirtySlices.length} dirty slices): ${((Date.now()-_tClear)/1000).toFixed(3)}s`);
            } else if (_hasPrevData) {
              // Fallback: bounding-box range scan (dirtySlices not yet stored, e.g. first run after migration)
              const _prevZ0: number = (_hasCropGeom && _prevCachedStats?.segZ0 != null)
                ? _prevCachedStats.segZ0 as number : 0;
              const _prevZ1: number = (_hasCropGeom && _prevCachedStats?.segZ1 != null)
                ? _prevCachedStats.segZ1 as number : merged_derivedImages.length;
              const scanZ0 = _hasCropGeom ? Math.min(_prevZ0, _segZ0) : 0;
              const scanZ1 = _hasCropGeom ? Math.max(_prevZ1, _segZ1) : merged_derivedImages.length;
              for (let i = scanZ0; i < scanZ1; i++) {
                const sd = (merged_derivedImages[i].voxelManager as csTypes.IVoxelManager<number>).getScalarData();
                for (let j = 0; j < sd.length; j++) {
                  if (sd[j] === segmentNumber) sd[j] = 0;
                }
              }
              console.log(`[nninter] clear fallback (${scanZ1-scanZ0} slices): ${((Date.now()-_tClear)/1000).toFixed(3)}s`);
            } else {
              // Brand-new segment — nothing to clear, skip entirely
              console.log(`[nninter] clear skipped (new segment)`);
            }

            // ── Pass 2: Write new pixels from crop only ───────────────────────
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

            if(flipped){
              merged_derivedImages.reverse();
            }
          }

        }


          const derivedImageIds = merged_derivedImages.map(image => image.imageId);
          console.log(`Just after derivedImageIds: ${(Date.now() - start)/1000} Seconds`);
          segments[segmentNumber] = {
            segmentIndex: segmentNumber,
            // Keep a pre-existing (or user-renamed) label; only name brand-new
            // segments by their index ("Segment 1", "Segment 2", …) instead of
            // labelling every object "nnInteractive".
            label: existingSegments[segmentNumber]?.label || `Segment ${segmentNumber}`,
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
            }
          };
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
            activeSegmentation,
            currentImageIdIndex,
            z_range,
          });
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
    'applyNninterManualCorrection',
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
  });

  return {
    actions,
    definitions,
    defaultContext: 'DEFAULT',
  };
};

export default commandsModule;
