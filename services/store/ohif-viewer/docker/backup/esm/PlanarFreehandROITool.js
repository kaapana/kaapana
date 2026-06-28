import { CONSTANTS, getEnabledElement, VolumeViewport, utilities as csUtils, } from '@cornerstonejs/core';
import { vec3 } from 'gl-matrix';
import { getCalibratedLengthUnitsAndScale } from '../../utilities/getCalibratedUnits';
import * as math from '../../utilities/math';
import { polyline } from '../../utilities/math';
import { filterAnnotationsForDisplay } from '../../utilities/planar';
import throttle from '../../utilities/throttle';
import { getViewportIdsWithToolToRender } from '../../utilities/viewportFilters';
import triggerAnnotationRenderForViewportIds from '../../utilities/triggerAnnotationRenderForViewportIds';
import registerDrawLoop from './planarFreehandROITool/drawLoop';
import registerEditLoopCommon from './planarFreehandROITool/editLoopCommon';
import registerClosedContourEditLoop from './planarFreehandROITool/closedContourEditLoop';
import registerOpenContourEditLoop from './planarFreehandROITool/openContourEditLoop';
import registerOpenContourEndEditLoop from './planarFreehandROITool/openContourEndEditLoop';
import registerRenderMethods from './planarFreehandROITool/renderMethods';
import { triggerAnnotationModified } from '../../stateManagement/annotation/helpers/state';
import { drawLinkedTextBox } from '../../drawingSvg';
import { getTextBoxCoordsCanvas } from '../../utilities/drawing';
import { getLineSegmentIntersectionsCoordinates } from '../../utilities/math/polyline';
import { isViewportPreScaled } from '../../utilities/viewport/isViewportPreScaled';
import { BasicStatsCalculator } from '../../utilities/math/basic';
import calculatePerimeter from '../../utilities/contours/calculatePerimeter';
import ContourSegmentationBaseTool from '../base/ContourSegmentationBaseTool';
import { KeyboardBindings, ChangeTypes } from '../../enums';
import { getPixelValueUnits } from '../../utilities/getPixelValueUnits';
const { pointCanProjectOnLine } = polyline;
const { EPSILON } = CONSTANTS;
const PARALLEL_THRESHOLD = 1 - EPSILON;
class PlanarFreehandROITool extends ContourSegmentationBaseTool {
    static { this.toolName = 'PlanarFreehandROI'; }
    constructor(toolProps = {}, defaultToolProps = {
        supportedInteractionTypes: ['Mouse', 'Touch'],
        configuration: {
            storePointData: false,
            shadow: true,
            preventHandleOutsideImage: false,
            contourHoleAdditionModifierKey: KeyboardBindings.Shift,
            alwaysRenderOpenContourHandles: {
                enabled: false,
                radius: 2,
            },
            allowOpenContours: true,
            closeContourProximity: 10,
            checkCanvasEditFallbackProximity: 6,
            makeClockWise: true,
            subPixelResolution: 4,
            smoothing: {
                smoothOnAdd: false,
                smoothOnEdit: false,
                knotsRatioPercentageOnAdd: 40,
                knotsRatioPercentageOnEdit: 40,
            },
            interpolation: {
                enabled: false,
                onInterpolationComplete: null,
            },
            decimate: {
                enabled: false,
                epsilon: 0.1,
            },
            displayOnePointAsCrosshairs: false,
            calculateStats: true,
            getTextLines: defaultGetTextLines,
            statsCalculator: BasicStatsCalculator,
        },
    }) {
        super(toolProps, defaultToolProps);
        this.isDrawing = false;
        this.isEditingClosed = false;
        this.isEditingOpen = false;
        this.addNewAnnotation = (evt) => {
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            const annotation = this.createAnnotation(evt);
            this.addAnnotation(annotation, element);
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.activateDraw(evt, annotation, viewportIdsToRender);
            evt.preventDefault();
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            return annotation;
        };
        this._addNewAnnotationFromIndex = (element, idxPos, closed = false, neg = false, SegmentNumber, segmentationId) => {
            const enabledElement = getEnabledElement(element);
            const { viewport, renderingEngine } = enabledElement;
            const image = this.getTargetImageData(this.getTargetId(viewport));
            const { imageData } = image;
            let boundary = idxPos.map(array => csUtils.transformIndexToWorld(imageData, array));
            const annotation = (this.constructor).createAnnotation({ metadata: viewport.getViewReference({sliceIndex: idxPos[0][2]}) },{
                data: {
                    contour: {
                        polyline: [...boundary],
                        closed: closed,
                    },
                    label: '',
                    cachedStats: {[this.getTargetId(viewport)]: {}},
                },
                interpolationUID: '',
                autoGenerated: false,
            });
            annotation.metadata.neg = neg;
            annotation.metadata.SegmentNumber = SegmentNumber;
            annotation.metadata.segmentationId = segmentationId;
            annotation.metadata.toolLoad = true;
            this._calculateCachedStats(annotation, viewport, renderingEngine, enabledElement);
            this.addAnnotation(annotation, element);
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.editData = {
                annotation,
                viewportIdsToRender,
                newAnnotation: true,
            };
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            return annotation;
        }
        this.handleSelectedCallback = (evt, annotation, handle) => {
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.activateOpenContourEndEdit(evt, annotation, viewportIdsToRender, handle);
        };
        this.toolSelectedCallback = (evt, annotation) => {
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            if (annotation.data.contour.closed) {
                this.activateClosedContourEdit(evt, annotation, viewportIdsToRender);
            }
            else {
                this.activateOpenContourEdit(evt, annotation, viewportIdsToRender);
            }
            evt.preventDefault();
        };
        this.isPointNearTool = (element, annotation, canvasCoords, proximity) => {
            const enabledElement = getEnabledElement(element);
            const { viewport } = enabledElement;
            const { polyline: points } = annotation.data.contour;
            let previousPoint = viewport.worldToCanvas(points[0]);
            for (let i = 1; i < points.length; i++) {
                const p1 = previousPoint;
                const p2 = viewport.worldToCanvas(points[i]);
                const canProject = pointCanProjectOnLine(canvasCoords, p1, p2, proximity);
                if (canProject) {
                    return true;
                }
                previousPoint = p2;
            }
            if (!annotation.data.contour.closed) {
                return false;
            }
            const pStart = viewport.worldToCanvas(points[0]);
            const pEnd = viewport.worldToCanvas(points[points.length - 1]);
            return pointCanProjectOnLine(canvasCoords, pStart, pEnd, proximity);
        };
        this.cancel = (element) => {
            const isDrawing = this.isDrawing;
            const isEditingOpen = this.isEditingOpen;
            const isEditingClosed = this.isEditingClosed;
            if (isDrawing) {
                this.cancelDrawing(element);
            }
            else if (isEditingOpen) {
                this.cancelOpenContourEdit(element);
            }
            else if (isEditingClosed) {
                this.cancelClosedContourEdit(element);
            }
        };
        this._calculateCachedStats = (annotation, viewport, renderingEngine, enabledElement) => {
            const { data } = annotation;
            const { cachedStats } = data;
            const { polyline: points, closed } = data.contour;
            const targetIds = Object.keys(cachedStats);
            for (let i = 0; i < targetIds.length; i++) {
                const targetId = targetIds[i];
                const image = this.getTargetImageData(targetId);
                if (!image) {
                    continue;
                }

                let sliceIndex = 0
                if (targetId.startsWith('imageId:') || targetId.startsWith('volumeId:')) {
                    sliceIndex = viewport.getCurrentImageIdIndex();
                }

                const { imageData, metadata } = image;
                const canvasCoordinates = points.map((p) => viewport.worldToCanvas(p));
                const modalityUnitOptions = {
                    isPreScaled: isViewportPreScaled(viewport, targetId),
                    isSuvScaled: this.isSuvScaled(viewport, targetId, annotation.metadata.referencedImageId),
                };
                const modalityUnit = getPixelValueUnits(metadata.Modality, annotation.metadata.referencedImageId, modalityUnitOptions);
                const calibratedScale = getCalibratedLengthUnitsAndScale(image, () => {
                    const polyline = data.contour.polyline;
                    const numPoints = polyline.length;
                    const projectedPolyline = new Array(numPoints);
                    for (let i = 0; i < numPoints; i++) {
                        projectedPolyline[i] = viewport.worldToCanvas(polyline[i]);
                    }
                    const { maxX: canvasMaxX, maxY: canvasMaxY, minX: canvasMinX, minY: canvasMinY, } = math.polyline.getAABB(projectedPolyline);
                    const topLeftBBWorld = viewport.canvasToWorld([canvasMinX, canvasMinY]);
                    const topLeftBBIndex = csUtils.transformWorldToIndex(imageData, topLeftBBWorld);
                    const bottomRightBBWorld = viewport.canvasToWorld([
                        canvasMaxX,
                        canvasMaxY,
                    ]);
                    const bottomRightBBIndex = csUtils.transformWorldToIndex(imageData, bottomRightBBWorld);
                    return [topLeftBBIndex, bottomRightBBIndex];
                });
                if(annotation.metadata.toolName === 'PlanarFreehandROI2'){
                    this.updateOpenCachedStats({
                        metadata,
                        imageData,
                        canvasCoordinates,
                        points,
                        sliceIndex,
                        targetId,
                        cachedStats,
                        modalityUnit,
                        calibratedScale,
                    });
                }
                else if (closed) {
                    this.updateClosedCachedStats({
                        targetId,
                        viewport,
                        canvasCoordinates,
                        points,
                        imageData,
                        metadata,
                        cachedStats,
                        modalityUnit,
                        calibratedScale,
                        sliceIndex,
                    });
                }
                else {
                    this.updateOpenCachedStats({
                        metadata,
                        imageData,
                        canvasCoordinates,
                        points,
                        sliceIndex,
                        targetId,
                        cachedStats,
                        modalityUnit,
                        calibratedScale,
                    });
                }
            }
            const invalidated = annotation.invalidated;
            annotation.invalidated = false;
            if (invalidated) {
                triggerAnnotationModified(annotation, enabledElement.viewport.element, ChangeTypes.StatsUpdated);
            }
            return cachedStats;
        };
        this._renderStats = (annotation, viewport, enabledElement, svgDrawingHelper) => {
            const { data } = annotation;
            const targetId = this.getTargetId(viewport);
            const styleSpecifier = {
                toolGroupId: this.toolGroupId,
                toolName: this.getToolName(),
                viewportId: enabledElement.viewport.id,
                annotationUID: annotation.annotationUID,
            };
            const options = this.getLinkedTextBoxStyle(styleSpecifier, annotation);
            // Do not render text box for now
            options.visibility = false;
            if (!options.visibility) {
                return;
            }
            const textLines = this.configuration.getTextLines(data, targetId);
            if (!textLines || textLines.length === 0) {
                return;
            }
            const canvasCoordinates = data.contour.polyline.map((p) => viewport.worldToCanvas(p));
            if (!data.handles.textBox.hasMoved) {
                const canvasTextBoxCoords = getTextBoxCoordsCanvas(canvasCoordinates);
                data.handles.textBox.worldPosition =
                    viewport.canvasToWorld(canvasTextBoxCoords);
            }
            const textBoxPosition = viewport.worldToCanvas(data.handles.textBox.worldPosition);
            const textBoxUID = '1';
            const boundingBox = drawLinkedTextBox(svgDrawingHelper, annotation.annotationUID ?? '', textBoxUID, textLines, textBoxPosition, canvasCoordinates, {}, options);
            const { x: left, y: top, width, height } = boundingBox;
            data.handles.textBox.worldBoundingBox = {
                topLeft: viewport.canvasToWorld([left, top]),
                topRight: viewport.canvasToWorld([left + width, top]),
                bottomLeft: viewport.canvasToWorld([left, top + height]),
                bottomRight: viewport.canvasToWorld([left + width, top + height]),
            };
        };
        registerDrawLoop(this);
        registerEditLoopCommon(this);
        registerClosedContourEditLoop(this);
        registerOpenContourEditLoop(this);
        registerOpenContourEndEditLoop(this);
        registerRenderMethods(this);
        this._throttledCalculateCachedStats = throttle(this._calculateCachedStats, 100, { trailing: true });
    }
    filterInteractableAnnotationsForElement(element, annotations) {
        if (!annotations || !annotations.length) {
            return;
        }
        const enabledElement = getEnabledElement(element);
        const { viewport } = enabledElement;
        let annotationsToDisplay;
        if (viewport instanceof VolumeViewport) {
            const camera = viewport.getCamera();
            const { spacingInNormalDirection } = csUtils.getTargetVolumeAndSpacingInNormalDir(viewport, camera);
            annotationsToDisplay = this.filterAnnotationsWithinSlice(annotations, camera, spacingInNormalDirection);
        }
        else {
            annotationsToDisplay = filterAnnotationsForDisplay(viewport, annotations);
        }
        return annotationsToDisplay;
    }
    filterAnnotationsWithinSlice(annotations, camera, spacingInNormalDirection) {
        const { viewPlaneNormal } = camera;
        const annotationsWithParallelNormals = annotations.filter((td) => {
            const annotationViewPlaneNormal = td.metadata.viewPlaneNormal;
            const isParallel = Math.abs(vec3.dot(viewPlaneNormal, annotationViewPlaneNormal)) >
                PARALLEL_THRESHOLD;
            return annotationViewPlaneNormal && isParallel;
        });
        if (!annotationsWithParallelNormals.length) {
            return [];
        }
        const halfSpacingInNormalDirection = spacingInNormalDirection / 2;
        const { focalPoint } = camera;
        const annotationsWithinSlice = [];
        for (const annotation of annotationsWithParallelNormals) {
            const data = annotation.data;
            const point = data.contour.polyline[0];
            if (!annotation.isVisible) {
                continue;
            }
            const dir = vec3.create();
            vec3.sub(dir, focalPoint, point);
            const dot = vec3.dot(dir, viewPlaneNormal);
            if (Math.abs(dot) < halfSpacingInNormalDirection) {
                annotationsWithinSlice.push(annotation);
            }
        }
        return annotationsWithinSlice;
    }
    isContourSegmentationTool() {
        return false;
    }
    createAnnotation(evt) {
        const worldPos = evt.detail.currentPoints.world;
        const contourAnnotation = super.createAnnotation(evt);
        const onInterpolationComplete = (annotation) => {
            annotation.data.handles.points.length = 0;
        };
        const annotation = csUtils.deepMerge(contourAnnotation, {
            data: {
                contour: {
                    polyline: [[...worldPos]],
                },
                label: '',
                cachedStats: {},
            },
            onInterpolationComplete,
        });
        return annotation;
    }
    getAnnotationStyle(context) {
        return super.getAnnotationStyle(context);
    }
    renderAnnotationInstance(renderContext) {
        const { enabledElement, targetId, svgDrawingHelper } = renderContext;
        const annotation = renderContext.annotation;
        let renderStatus = false;
        const { viewport, renderingEngine } = enabledElement;
        const isDrawing = this.isDrawing;
        const isEditingOpen = this.isEditingOpen;
        const isEditingClosed = this.isEditingClosed;
        if(annotation.metadata.toolName === 'PlanarFreehandROI3'){
            this.configuration.allowOpenContours = false;
        }
        if (!(isDrawing || isEditingOpen || isEditingClosed)) {
            if (this.configuration.displayOnePointAsCrosshairs &&
                annotation.data.contour.polyline.length === 1) {
                this.renderPointContourWithMarker(enabledElement, svgDrawingHelper, annotation);
            }
            else {
                this.renderContour(enabledElement, svgDrawingHelper, annotation);
            }
        }
        else {
            const activeAnnotationUID = this.commonData.annotation.annotationUID;
            if (annotation.annotationUID === activeAnnotationUID) {
                if (isDrawing) {
                    this.renderContourBeingDrawn(enabledElement, svgDrawingHelper, annotation);
                }
                else if (isEditingClosed) {
                    this.renderClosedContourBeingEdited(enabledElement, svgDrawingHelper, annotation);
                }
                else if (isEditingOpen) {
                    this.renderOpenContourBeingEdited(enabledElement, svgDrawingHelper, annotation);
                }
                else {
                    throw new Error(`Unknown ${this.getToolName()} annotation rendering state`);
                }
            }
            else {
                if (this.configuration.displayOnePointAsCrosshairs &&
                    annotation.data.contour.polyline.length === 1) {
                    this.renderPointContourWithMarker(enabledElement, svgDrawingHelper, annotation);
                }
                else {
                    this.renderContour(enabledElement, svgDrawingHelper, annotation);
                }
            }
            renderStatus = true;
        }
        if (!this.configuration.calculateStats) {
            return;
        }
        this._calculateStatsIfActive(annotation, targetId, viewport, renderingEngine, enabledElement);
        this._renderStats(annotation, viewport, enabledElement, svgDrawingHelper);
        return renderStatus;
    }
    _calculateStatsIfActive(annotation, targetId, viewport, renderingEngine, enabledElement) {
        const activeAnnotationUID = this.commonData?.annotation.annotationUID;
        if (annotation.annotationUID === activeAnnotationUID &&
            !this.commonData?.movingTextBox) {
            return;
        }
        if (!this.commonData?.movingTextBox) {
            const { data } = annotation;
            if (!data.cachedStats[targetId]?.unit) {
                data.cachedStats[targetId] = {
                    Modality: null,
                    area: null,
                    max: null,
                    mean: null,
                    stdDev: null,
                    areaUnit: null,
                    unit: null,
                };
                this._calculateCachedStats(annotation, viewport, renderingEngine, enabledElement);
            }
            else if (annotation.invalidated) {
                this._throttledCalculateCachedStats(annotation, viewport, renderingEngine, enabledElement);
            }
        }
    }
    updateClosedCachedStats({ viewport, points, imageData, metadata, cachedStats, targetId, modalityUnit, canvasCoordinates, calibratedScale,sliceIndex }) {
        const { scale, areaUnit, unit } = calibratedScale;
        let boundary = points.map(array => csUtils.transformWorldToIndex(imageData, array));
        // z-coordinate should be assigned differently for stack viewport (imageId) and volume viewport (volumeId)
        if (targetId.startsWith('imageId:')){
            boundary = boundary.map(array => [Math.round(array[0]),Math.round(array[1]),sliceIndex]);
        }
        else if (targetId.startsWith('volumeId:')){
            const axialViewport = services.cornerstoneViewportService.getCornerstoneViewport('mpr-axial') 
                || services.cornerstoneViewportService.getCornerstoneViewport('default');
            
            if (!axialViewport) {
                return;
            }

            const imageIdsInVolume = axialViewport.getImageIds();
            if (!imageIdsInVolume?.length) {
                return;
            }

            // Get active viewport data
            const { activeViewportId, viewports } = services.viewportGridService.getState();
            const activeViewportData = viewports.get(activeViewportId);
            const displaySetInstanceUID = activeViewportData?.displaySetInstanceUIDs?.[0];
            
            if (!displaySetInstanceUID) {
                return;
            }

            // Find matching display set (manual loop for optimal performance)
            let currentDisplaySet;
            const displaySets = services.displaySetService.activeDisplaySets;
            for (let i = 0; i < displaySets.length; i++) {
                if (displaySets[i].displaySetInstanceUID === displaySetInstanceUID) {
                    currentDisplaySet = displaySets[i];
                    break;
                }
            }

            // Check if imageIds are flipped and correct z-coordinate if needed
            if (currentDisplaySet?.imageIds?.[0] && 
                imageIdsInVolume[0] !== currentDisplaySet.imageIds[0]) {
                const imageIdsLength = imageIdsInVolume.length;
                boundary = boundary.map(array => [
                    Math.round(array[0]),
                    Math.round(array[1]),
                    imageIdsLength - Math.round(array[2]) - 1
                ]);
            }            
        }
        const { voxelManager } = viewport.getImageData();
        const canvasPoint = canvasCoordinates[0];
        const originalWorldPoint = viewport.canvasToWorld(canvasPoint);
        const deltaXPoint = viewport.canvasToWorld([
            canvasPoint[0] + 1,
            canvasPoint[1],
        ]);
        const deltaYPoint = viewport.canvasToWorld([
            canvasPoint[0],
            canvasPoint[1] + 1,
        ]);
        const deltaInX = vec3.distance(originalWorldPoint, deltaXPoint);
        const deltaInY = vec3.distance(originalWorldPoint, deltaYPoint);
        const worldPosIndex = csUtils.transformWorldToIndex(imageData, points[0]);
        worldPosIndex[0] = Math.floor(worldPosIndex[0]);
        worldPosIndex[1] = Math.floor(worldPosIndex[1]);
        worldPosIndex[2] = Math.floor(worldPosIndex[2]);
        let iMin = worldPosIndex[0];
        let iMax = worldPosIndex[0];
        let jMin = worldPosIndex[1];
        let jMax = worldPosIndex[1];
        let kMin = worldPosIndex[2];
        let kMax = worldPosIndex[2];
        for (let j = 1; j < points.length; j++) {
            const worldPosIndex = csUtils.transformWorldToIndex(imageData, points[j]);
            worldPosIndex[0] = Math.floor(worldPosIndex[0]);
            worldPosIndex[1] = Math.floor(worldPosIndex[1]);
            worldPosIndex[2] = Math.floor(worldPosIndex[2]);
            iMin = Math.min(iMin, worldPosIndex[0]);
            iMax = Math.max(iMax, worldPosIndex[0]);
            jMin = Math.min(jMin, worldPosIndex[1]);
            jMax = Math.max(jMax, worldPosIndex[1]);
            kMin = Math.min(kMin, worldPosIndex[2]);
            kMax = Math.max(kMax, worldPosIndex[2]);
        }
        const worldPosIndex2 = csUtils.transformWorldToIndex(imageData, points[1]);
        worldPosIndex2[0] = Math.floor(worldPosIndex2[0]);
        worldPosIndex2[1] = Math.floor(worldPosIndex2[1]);
        worldPosIndex2[2] = Math.floor(worldPosIndex2[2]);
        let area = polyline.getArea(canvasCoordinates) / scale / scale;
        area *= deltaInX * deltaInY;
        const iDelta = 0.01 * (iMax - iMin);
        const jDelta = 0.01 * (jMax - jMin);
        const kDelta = 0.01 * (kMax - kMin);
        iMin = Math.floor(iMin - iDelta);
        iMax = Math.ceil(iMax + iDelta);
        jMin = Math.floor(jMin - jDelta);
        jMax = Math.ceil(jMax + jDelta);
        kMin = Math.floor(kMin - kDelta);
        kMax = Math.ceil(kMax + kDelta);
        const boundsIJK = [
            [iMin, iMax],
            [jMin, jMax],
            [kMin, kMax],
        ];
        const worldPosEnd = imageData.indexToWorld([iMax, jMax, kMax]);
        const canvasPosEnd = viewport.worldToCanvas(worldPosEnd);
        let curRow = 0;
        let intersections = [];
        let intersectionCounter = 0;
        const pointsInShape = voxelManager.forEach(this.configuration.statsCalculator.statsCallback, {
            imageData,
            isInObject: (pointLPS, _pointIJK) => {
                let result = true;
                const point = viewport.worldToCanvas(pointLPS);
                if (point[1] != curRow) {
                    intersectionCounter = 0;
                    curRow = point[1];
                    intersections = getLineSegmentIntersectionsCoordinates(canvasCoordinates, point, [canvasPosEnd[0], point[1]]);
                    intersections.sort((function (index) {
                        return function (a, b) {
                            return a[index] === b[index]
                                ? 0
                                : a[index] < b[index]
                                    ? -1
                                    : 1;
                        };
                    })(0));
                }
                if (intersections.length && point[0] > intersections[0][0]) {
                    intersections.shift();
                    intersectionCounter++;
                }
                if (intersectionCounter % 2 === 0) {
                    result = false;
                }
                return result;
            },
            boundsIJK,
            returnPoints: this.configuration.storePointData,
        });
        const stats = this.configuration.statsCalculator.getStatistics();
        cachedStats[targetId] = {
            Modality: metadata.Modality,
            area,
            perimeter: calculatePerimeter(canvasCoordinates, closed) / scale,
            mean: stats.mean?.value,
            max: stats.max?.value,
            stdDev: stats.stdDev?.value,
            statsArray: stats.array,
            pointsInShape: pointsInShape,
            boundary: boundary,
            areaUnit,
            modalityUnit,
            unit,
        };
    }
    updateOpenCachedStats({ targetId, metadata, imageData, canvasCoordinates, points, sliceIndex, cachedStats, modalityUnit, calibratedScale, }) {
        const { scale, unit } = calibratedScale;
        let polyline = points.map(array => csUtils.transformWorldToIndex(imageData, array));
        // for StackViewport, the z-coordinate is the sliceIndex
        if (targetId.startsWith('imageId:')) {
            polyline = polyline.map(array => [Math.round(array[0]),Math.round(array[1]),sliceIndex]);
        }
        // for VolumeViewport in MPR
        if (targetId.startsWith('volumeId:')) {
            // Try to get axial viewport (mpr-axial first, then default fallback)
            const axialViewport = services.cornerstoneViewportService.getCornerstoneViewport('mpr-axial') 
                || services.cornerstoneViewportService.getCornerstoneViewport('default');
            
            if (!axialViewport) {
                return;
            }

            const imageIdsInVolume = axialViewport.getImageIds();
            if (!imageIdsInVolume?.length) {
                return;
            }

            // Get active viewport data
            const { activeViewportId, viewports } = services.viewportGridService.getState();
            const activeViewportData = viewports.get(activeViewportId);
            const displaySetInstanceUID = activeViewportData?.displaySetInstanceUIDs?.[0];
            
            if (!displaySetInstanceUID) {
                return;
            }

            // Find matching display set (manual loop for optimal performance)
            let currentDisplaySet;
            const displaySets = services.displaySetService.activeDisplaySets;
            for (let i = 0; i < displaySets.length; i++) {
                if (displaySets[i].displaySetInstanceUID === displaySetInstanceUID) {
                    currentDisplaySet = displaySets[i];
                    break;
                }
            }

            // Check if imageIds are flipped and correct z-coordinate if needed
            if (currentDisplaySet?.imageIds?.[0] && 
                imageIdsInVolume[0] !== currentDisplaySet.imageIds[0]) {
                const imageIdsLength = imageIdsInVolume.length;
                polyline = polyline.map(array => [
                    Math.round(array[0]),
                    Math.round(array[1]),
                    imageIdsLength - Math.round(array[2]) - 1
                ]);
            }
        }
        
        cachedStats[targetId] = {
            Modality: metadata.Modality,
            length: calculatePerimeter(canvasCoordinates, false) / scale,
            modalityUnit,
            unit,
            scribble: polyline,
        };
    }
}
function defaultGetTextLines(data, targetId) {
    const cachedVolumeStats = data.cachedStats[targetId];
    const { area, mean, stdDev, length, perimeter, max, isEmptyArea, unit, areaUnit, modalityUnit, } = cachedVolumeStats || {};
    const textLines = [];
    if (area) {
        const areaLine = isEmptyArea
            ? `Area: Oblique not supported`
            : `Area: ${csUtils.roundNumber(area)} ${areaUnit}`;
        textLines.push(areaLine);
    }
    if (mean) {
        textLines.push(`Mean: ${csUtils.roundNumber(mean)} ${modalityUnit}`);
    }
    if (Number.isFinite(max)) {
        textLines.push(`Max: ${csUtils.roundNumber(max)} ${modalityUnit}`);
    }
    if (stdDev) {
        textLines.push(`Std Dev: ${csUtils.roundNumber(stdDev)} ${modalityUnit}`);
    }
    if (perimeter) {
        textLines.push(`Perimeter: ${csUtils.roundNumber(perimeter)} ${unit}`);
    }
    if (length) {
        textLines.push(`${csUtils.roundNumber(length)} ${unit}`);
    }
    return textLines;
}
export default PlanarFreehandROITool;
