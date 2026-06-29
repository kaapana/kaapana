import { getEnabledElement, utilities as csUtils } from '@cornerstonejs/core';
import {
  annotation as cornerstoneAnnotation,
  ProbeTool,
  RectangleROITool,
  PlanarFreehandROITool,
  utilities as csToolsUtils,
} from '@cornerstonejs/tools';

function markPromptAnnotation(annotation: any, neg: boolean, segmentNumber: number, segmentationId: string) {
  annotation.metadata.neg = neg;
  annotation.metadata.SegmentNumber = segmentNumber;
  annotation.metadata.segmentationId = segmentationId;
  annotation.metadata.toolLoad = true;
}

function getViewportContext(element: HTMLDivElement) {
  const enabledElement = getEnabledElement(element);
  const { viewport, renderingEngine } = enabledElement;
  const image = viewport.getImageData?.();
  const imageData = image?.imageData ?? image;

  return { enabledElement, viewport, renderingEngine, imageData };
}

function triggerToolRender(tool: any, element: HTMLDivElement, annotation: any) {
  const viewportIdsToRender = csToolsUtils.viewportFilters.getViewportIdsWithToolToRender(
    element,
    tool.getToolName()
  );

  tool.editData = {
    annotation,
    viewportIdsToRender,
    newAnnotation: true,
  };

  csToolsUtils.triggerAnnotationRenderForViewportIds(viewportIdsToRender);
}

export class Probe2Tool extends ProbeTool {
  static toolName = 'Probe2';

  _addNewAnnotationFromIndex(
    element: HTMLDivElement,
    idxPos: number[],
    neg = false,
    segmentNumber: number,
    segmentationId: string
  ) {
    const { enabledElement, viewport, renderingEngine, imageData } = getViewportContext(element);
    const worldPos = imageData.indexToWorld?.(idxPos) ?? csUtils.transformIndexToWorld(imageData, idxPos);

    const annotation = (this.constructor as any).createAnnotation(
      { metadata: viewport.getViewReference({ sliceIndex: idxPos[2] }) },
      {
        data: {
          handles: { points: [[...worldPos]] },
          cachedStats: { [this.getTargetId(viewport)]: {} },
        },
      }
    );

    markPromptAnnotation(annotation, neg, segmentNumber, segmentationId);
    (this as any)._calculateCachedStats?.(annotation, renderingEngine, enabledElement);
    cornerstoneAnnotation.state.addAnnotation(annotation, element);
    triggerToolRender(this, element, annotation);
    return annotation;
  }
}

export class RectangleROI2Tool extends RectangleROITool {
  static toolName = 'RectangleROI2';

  _addNewAnnotationFromIndex(
    element: HTMLDivElement,
    idxPos: number[][],
    neg = false,
    segmentNumber: number,
    segmentationId: string
  ) {
    const { enabledElement, viewport, renderingEngine, imageData } = getViewportContext(element);
    const tl = imageData.indexToWorld?.(idxPos[0]) ?? csUtils.transformIndexToWorld(imageData, idxPos[0]);
    const trIndex = [idxPos[1][0], idxPos[0][1], idxPos[0][2]];
    const blIndex = [idxPos[0][0], idxPos[1][1], idxPos[0][2]];
    const tr = imageData.indexToWorld?.(trIndex) ?? csUtils.transformIndexToWorld(imageData, trIndex);
    const bl = imageData.indexToWorld?.(blIndex) ?? csUtils.transformIndexToWorld(imageData, blIndex);
    const br = imageData.indexToWorld?.(idxPos[1]) ?? csUtils.transformIndexToWorld(imageData, idxPos[1]);

    const annotation = (this.constructor as any).createAnnotation(
      { metadata: viewport.getViewReference({ sliceIndex: idxPos[0][2] }) },
      {
        data: {
          handles: {
            points: [[...tl], [...tr], [...bl], [...br]],
            activeHandleIndex: null,
          },
          cachedStats: { [this.getTargetId(viewport)]: {} },
        },
      }
    );

    const { viewPlaneNormal, viewUp } = viewport.getCamera();
    annotation.metadata.viewPlaneNormal = viewPlaneNormal;
    annotation.metadata.viewUp = viewUp;
    markPromptAnnotation(annotation, neg, segmentNumber, segmentationId);
    (this as any)._calculateCachedStats?.(annotation, renderingEngine, enabledElement);
    cornerstoneAnnotation.state.addAnnotation(annotation, element);
    triggerToolRender(this, element, annotation);
    return annotation;
  }
}

export class PlanarFreehandROI2Tool extends PlanarFreehandROITool {
  static toolName = 'PlanarFreehandROI2';

  _addNewAnnotationFromIndex(
    element: HTMLDivElement,
    idxPos: number[][],
    closed = false,
    neg = false,
    segmentNumber: number,
    segmentationId: string
  ) {
    return addFreehandPromptAnnotation(this, element, idxPos, closed, neg, segmentNumber, segmentationId);
  }
}

export class PlanarFreehandROI3Tool extends PlanarFreehandROITool {
  static toolName = 'PlanarFreehandROI3';

  _addNewAnnotationFromIndex(
    element: HTMLDivElement,
    idxPos: number[][],
    closed = true,
    neg = false,
    segmentNumber: number,
    segmentationId: string
  ) {
    return addFreehandPromptAnnotation(this, element, idxPos, closed, neg, segmentNumber, segmentationId);
  }
}

function addFreehandPromptAnnotation(
  tool: any,
  element: HTMLDivElement,
  idxPos: number[][],
  closed: boolean,
  neg: boolean,
  segmentNumber: number,
  segmentationId: string
) {
  const { enabledElement, viewport, renderingEngine, imageData } = getViewportContext(element);
  const boundary = idxPos.map(
    point => imageData.indexToWorld?.(point) ?? csUtils.transformIndexToWorld(imageData, point)
  );

  const annotation = (tool.constructor as any).createAnnotation(
    { metadata: viewport.getViewReference({ sliceIndex: idxPos[0][2] }) },
    {
      data: {
        contour: {
          polyline: [...boundary],
          closed,
        },
        label: '',
        cachedStats: { [tool.getTargetId(viewport)]: {} },
      },
      interpolationUID: '',
      autoGenerated: false,
    }
  );

  markPromptAnnotation(annotation, neg, segmentNumber, segmentationId);
  tool._calculateCachedStats?.(annotation, viewport, renderingEngine, enabledElement);

  if (typeof tool.addAnnotation === 'function') {
    tool.addAnnotation(annotation, element);
  } else {
    cornerstoneAnnotation.state.addAnnotation(annotation, element);
  }

  triggerToolRender(tool, element, annotation);
  return annotation;
}
