import { getEnabledElement, utilities } from '@cornerstonejs/core';
import { resetElementCursor, hideElementCursor, } from '../../../cursors/elementCursor';
import { ChangeTypes, Events } from '../../../enums';
import { state } from '../../../store/state';
import { vec3 } from 'gl-matrix';
import { shouldSmooth, getInterpolatedPoints, } from '../../../utilities/planarFreehandROITool/smoothPoints';
import getMouseModifierKey from '../../../eventDispatchers/shared/getMouseModifier';
import triggerAnnotationRenderForViewportIds from '../../../utilities/triggerAnnotationRenderForViewportIds';
import { triggerAnnotationModified, triggerContourAnnotationCompleted, } from '../../../stateManagement/annotation/helpers/state';
import findOpenUShapedContourVectorToPeak from './findOpenUShapedContourVectorToPeak';
import { polyline } from '../../../utilities/math';
import { removeAnnotation } from '../../../stateManagement/annotation/annotationState';
import { ContourWindingDirection } from '../../../types/ContourAnnotation';
const { addCanvasPointsToArray, pointsAreWithinCloseContourProximity, getFirstLineSegmentIntersectionIndexes, getSubPixelSpacingAndXYDirections, } = polyline;
function activateDraw(evt, annotation, viewportIdsToRender) {
    this.isDrawing = true;
    const eventDetail = evt.detail;
    const { currentPoints, element } = eventDetail;
    const canvasPos = currentPoints.canvas;
    const enabledElement = getEnabledElement(element);
    const { viewport } = enabledElement;
    const contourHoleProcessingEnabled = getMouseModifierKey(evt.detail.event) ===
        this.configuration.contourHoleAdditionModifierKey;
    const { spacing, xDir, yDir } = getSubPixelSpacingAndXYDirections(viewport, this.configuration.subPixelResolution) || {};
    if (!spacing || !xDir || !yDir) {
        return;
    }
    this.drawData = {
        canvasPoints: [canvasPos],
        polylineIndex: 0,
        contourHoleProcessingEnabled,
        newAnnotation: true,
    };
    this.commonData = {
        annotation,
        viewportIdsToRender,
        spacing,
        xDir,
        yDir,
        movingTextBox: false,
    };
    state.isInteractingWithTool = true;
    element.addEventListener(Events.MOUSE_UP, this.mouseUpDrawCallback);
    element.addEventListener(Events.MOUSE_DRAG, this.mouseDragDrawCallback);
    element.addEventListener(Events.MOUSE_CLICK, this.mouseUpDrawCallback);
    element.addEventListener(Events.TOUCH_END, this.mouseUpDrawCallback);
    element.addEventListener(Events.TOUCH_DRAG, this.mouseDragDrawCallback);
    element.addEventListener(Events.TOUCH_TAP, this.mouseUpDrawCallback);
 // hideElementCursor(element); //cursor visible
}
function deactivateDraw(element) {
    state.isInteractingWithTool = false;
    element.removeEventListener(Events.MOUSE_UP, this.mouseUpDrawCallback);
    element.removeEventListener(Events.MOUSE_DRAG, this.mouseDragDrawCallback);
    element.removeEventListener(Events.MOUSE_CLICK, this.mouseUpDrawCallback);
    element.removeEventListener(Events.TOUCH_END, this.mouseUpDrawCallback);
    element.removeEventListener(Events.TOUCH_DRAG, this.mouseDragDrawCallback);
    element.removeEventListener(Events.TOUCH_TAP, this.mouseUpDrawCallback);
 // resetElementCursor(element); //cursor visible
}
function mouseDragDrawCallback(evt) {
    const eventDetail = evt.detail;
    const { currentPoints, element } = eventDetail;
    const worldPos = currentPoints.world;
    const canvasPos = currentPoints.canvas;
    const enabledElement = getEnabledElement(element);
    const { viewport } = enabledElement;
    const { annotation, viewportIdsToRender, xDir, yDir, spacing, movingTextBox, } = this.commonData;
    const { polylineIndex, canvasPoints, newAnnotation } = this.drawData;
    this.createMemo(element, annotation, { newAnnotation });
    const lastCanvasPoint = canvasPoints[canvasPoints.length - 1];
    const lastWorldPoint = viewport.canvasToWorld(lastCanvasPoint);
    const worldPosDiff = vec3.create();
    vec3.subtract(worldPosDiff, worldPos, lastWorldPoint);
    const xDist = Math.abs(vec3.dot(worldPosDiff, xDir));
    const yDist = Math.abs(vec3.dot(worldPosDiff, yDir));
    if (xDist <= spacing[0] && yDist <= spacing[1]) {
        return;
    }
    if (movingTextBox) {
        this.isDrawing = false;
        const { deltaPoints } = eventDetail;
        const worldPosDelta = deltaPoints.world;
        const { textBox } = annotation.data.handles;
        const { worldPosition } = textBox;
        worldPosition[0] += worldPosDelta[0];
        worldPosition[1] += worldPosDelta[1];
        worldPosition[2] += worldPosDelta[2];
        textBox.hasMoved = true;
    }
    else {
            const crossingIndex = this.findCrossingIndexDuringCreate(evt);
            if (crossingIndex !== undefined && annotation.metadata.toolName !== 'PlanarFreehandROI2') {
                this.applyCreateOnCross(evt, crossingIndex);
            }
            else {
                const numPointsAdded = addCanvasPointsToArray(element, canvasPoints, canvasPos, this.commonData);
                this.drawData.polylineIndex = polylineIndex + numPointsAdded;
            }
            annotation.invalidated = true;
    }
    triggerAnnotationRenderForViewportIds(viewportIdsToRender);
    if (annotation.invalidated) {
        triggerAnnotationModified(annotation, element, ChangeTypes.HandlesUpdated);
    }
}
function mouseUpDrawCallback(evt) {
    const { allowOpenContours } = this.configuration;
    const { canvasPoints, contourHoleProcessingEnabled } = this.drawData;
    const firstPoint = canvasPoints[0];
    const lastPoint = canvasPoints[canvasPoints.length - 1];
    const eventDetail = evt.detail;
    const { element } = eventDetail;
    this.doneEditMemo();
    this.drawData.newAnnotation = false;
    if (allowOpenContours &&
        !pointsAreWithinCloseContourProximity(firstPoint, lastPoint, this.configuration.closeContourProximity)) {
        this.completeDrawOpenContour(element, { contourHoleProcessingEnabled });
    }
    else {
        this.completeDrawClosedContour(element, { contourHoleProcessingEnabled });
    }
}
function completeDrawClosedContour(element, options) {
    this.removeCrossedLinesOnCompleteDraw();
    const { canvasPoints } = this.drawData;
    const { contourHoleProcessingEnabled, minPointsToSave } = options ?? {};
    if (minPointsToSave && canvasPoints.length < minPointsToSave) {
        return false;
    }
    if (this.haltDrawing(element, canvasPoints)) {
        return false;
    }
    const { annotation, viewportIdsToRender } = this.commonData;
    const enabledElement = getEnabledElement(element);
    const { viewport, renderingEngine } = enabledElement;
    addCanvasPointsToArray(element, canvasPoints, canvasPoints[0], this.commonData);
    canvasPoints.pop();
    const updatedPoints = shouldSmooth(this.configuration, annotation)
        ? getInterpolatedPoints(this.configuration, canvasPoints)
        : canvasPoints;
    this.updateContourPolyline(annotation, {
        points: updatedPoints,
        closed: true,
        targetWindingDirection: ContourWindingDirection.Clockwise,
    }, viewport);
    const { textBox } = annotation.data.handles;
    if (!textBox?.hasMoved) {
        triggerContourAnnotationCompleted(annotation, contourHoleProcessingEnabled);
    }
    this.isDrawing = false;
    this.drawData = undefined;
    this.commonData = undefined;
    triggerAnnotationRenderForViewportIds(viewportIdsToRender);
    this.deactivateDraw(element);
    return true;
}
function removeCrossedLinesOnCompleteDraw() {
    const { canvasPoints } = this.drawData;
    const numPoints = canvasPoints.length;
    const endToStart = [canvasPoints[0], canvasPoints[numPoints - 1]];
    const canvasPointsMinusEnds = canvasPoints.slice(0, -1).slice(1);
    const lineSegment = getFirstLineSegmentIntersectionIndexes(canvasPointsMinusEnds, endToStart[0], endToStart[1], false);
    if (lineSegment) {
        const indexToRemoveUpTo = lineSegment[1];
        if (indexToRemoveUpTo === 1) {
            this.drawData.canvasPoints = canvasPoints.splice(1);
        }
        else {
            this.drawData.canvasPoints = canvasPoints.splice(0, indexToRemoveUpTo);
        }
    }
}
function completeDrawOpenContour(element, options) {
    const { canvasPoints } = this.drawData;
    const { contourHoleProcessingEnabled } = options ?? {};
    if (this.haltDrawing(element, canvasPoints)) {
        return false;
    }
    const { annotation, viewportIdsToRender } = this.commonData;
    const enabledElement = getEnabledElement(element);
    const { viewport, renderingEngine } = enabledElement;
    const updatedPoints = shouldSmooth(this.configuration, annotation)
        ? getInterpolatedPoints(this.configuration, canvasPoints)
        : canvasPoints;
    this.updateContourPolyline(annotation, {
        points: updatedPoints,
        closed: false,
    }, viewport);
    const { textBox } = annotation.data.handles;
    const worldPoints = annotation.data.contour.polyline;
    annotation.data.handles.points = [
        worldPoints[0],
        worldPoints[worldPoints.length - 1],
    ];
    if (annotation.data.isOpenUShapeContour) {
        annotation.data.openUShapeContourVectorToPeak =
            findOpenUShapedContourVectorToPeak(canvasPoints, viewport);
    }
    if (!textBox.hasMoved) {
        triggerContourAnnotationCompleted(annotation, contourHoleProcessingEnabled);
    }
    this.isDrawing = false;
    this.drawData = undefined;
    this.commonData = undefined;
    triggerAnnotationRenderForViewportIds(viewportIdsToRender);
    this.deactivateDraw(element);
    return true;
}
function findCrossingIndexDuringCreate(evt) {
    const eventDetail = evt.detail;
    const { currentPoints, lastPoints } = eventDetail;
    const canvasPos = currentPoints.canvas;
    const lastCanvasPoint = lastPoints.canvas;
    const { canvasPoints } = this.drawData;
    const pointsLessLastOne = canvasPoints.slice(0, -1);
    const lineSegment = getFirstLineSegmentIntersectionIndexes(pointsLessLastOne, canvasPos, lastCanvasPoint, false);
    if (lineSegment === undefined) {
        return;
    }
    const crossingIndex = lineSegment[0];
    return crossingIndex;
}
function applyCreateOnCross(evt, crossingIndex) {
    const eventDetail = evt.detail;
    const { element } = eventDetail;
    const { canvasPoints, contourHoleProcessingEnabled } = this.drawData;
    const { annotation, viewportIdsToRender } = this.commonData;
    addCanvasPointsToArray(element, canvasPoints, canvasPoints[crossingIndex], this.commonData);
    canvasPoints.pop();
    const remainingPoints = canvasPoints.slice(crossingIndex);
    const newArea = polyline.getArea(remainingPoints);
    if (utilities.isEqual(newArea, 0)) {
        canvasPoints.splice(crossingIndex + 1);
        return;
    }
    canvasPoints.splice(0, crossingIndex);
    const options = { contourHoleProcessingEnabled, minPointsToSave: 3 };
    if (this.completeDrawClosedContour(element, options)) {
        this.activateClosedContourEdit(evt, annotation, viewportIdsToRender);
    }
}
function cancelDrawing(element) {
    const { allowOpenContours } = this.configuration;
    const { canvasPoints, contourHoleProcessingEnabled } = this.drawData;
    const firstPoint = canvasPoints[0];
    const lastPoint = canvasPoints[canvasPoints.length - 1];
    if (allowOpenContours &&
        !pointsAreWithinCloseContourProximity(firstPoint, lastPoint, this.configuration.closeContourProximity)) {
        this.completeDrawOpenContour(element, { contourHoleProcessingEnabled });
    }
    else {
        this.completeDrawClosedContour(element, { contourHoleProcessingEnabled });
    }
}
function shouldHaltDrawing(canvasPoints, subPixelResolution) {
    // We need to support tiny scribbles as well
    const minPoints = 3; //Math.max(subPixelResolution * 3, 3);
    return canvasPoints.length < minPoints;
}
function haltDrawing(element, canvasPoints) {
    const { subPixelResolution } = this.configuration;
    if (shouldHaltDrawing(canvasPoints, subPixelResolution)) {
        const { annotation, viewportIdsToRender } = this.commonData;
        const enabledElement = getEnabledElement(element);
        const { renderingEngine } = enabledElement;
        removeAnnotation(annotation.annotationUID);
        this.isDrawing = false;
        this.drawData = undefined;
        this.commonData = undefined;
        triggerAnnotationRenderForViewportIds(viewportIdsToRender);
        this.deactivateDraw(element);
        return true;
    }
    return false;
}
function registerDrawLoop(toolInstance) {
    toolInstance.activateDraw = activateDraw.bind(toolInstance);
    toolInstance.deactivateDraw = deactivateDraw.bind(toolInstance);
    toolInstance.applyCreateOnCross = applyCreateOnCross.bind(toolInstance);
    toolInstance.findCrossingIndexDuringCreate =
        findCrossingIndexDuringCreate.bind(toolInstance);
    toolInstance.completeDrawOpenContour =
        completeDrawOpenContour.bind(toolInstance);
    toolInstance.removeCrossedLinesOnCompleteDraw =
        removeCrossedLinesOnCompleteDraw.bind(toolInstance);
    toolInstance.mouseDragDrawCallback = mouseDragDrawCallback.bind(toolInstance);
    toolInstance.mouseUpDrawCallback = mouseUpDrawCallback.bind(toolInstance);
    toolInstance.completeDrawClosedContour =
        completeDrawClosedContour.bind(toolInstance);
    toolInstance.cancelDrawing = cancelDrawing.bind(toolInstance);
    toolInstance.haltDrawing = haltDrawing.bind(toolInstance);
}
export default registerDrawLoop;
