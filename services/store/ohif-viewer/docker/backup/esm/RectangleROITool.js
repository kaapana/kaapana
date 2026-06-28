import { AnnotationTool } from '../base';
import { getEnabledElement, VolumeViewport, utilities as csUtils, getEnabledElementByViewportId, } from '@cornerstonejs/core';
import { getCalibratedLengthUnitsAndScale } from '../../utilities/getCalibratedUnits';
import throttle from '../../utilities/throttle';
import { addAnnotation, getAnnotations, removeAnnotation, } from '../../stateManagement';
import { isAnnotationLocked } from '../../stateManagement/annotation/annotationLocking';
import { isAnnotationVisible } from '../../stateManagement/annotation/annotationVisibility';
import { triggerAnnotationCompleted, triggerAnnotationModified, } from '../../stateManagement/annotation/helpers/state';
import { drawHandles as drawHandlesSvg, drawLinkedTextBox as drawLinkedTextBoxSvg, drawRectByCoordinates as drawRectSvg, } from '../../drawingSvg';
import { state } from '../../store/state';
import { ChangeTypes, Events } from '../../enums';
import { getViewportIdsWithToolToRender } from '../../utilities/viewportFilters';
import * as rectangle from '../../utilities/math/rectangle';
import { getTextBoxCoordsCanvas } from '../../utilities/drawing';
import getWorldWidthAndHeightFromCorners from '../../utilities/planar/getWorldWidthAndHeightFromCorners';
import { resetElementCursor, hideElementCursor, } from '../../cursors/elementCursor';
import triggerAnnotationRenderForViewportIds from '../../utilities/triggerAnnotationRenderForViewportIds';
import { getPixelValueUnits } from '../../utilities/getPixelValueUnits';
import { isViewportPreScaled } from '../../utilities/viewport/isViewportPreScaled';
import { BasicStatsCalculator } from '../../utilities/math/basic';
const { transformWorldToIndex } = csUtils;
class RectangleROITool extends AnnotationTool {
    static { this.toolName = 'RectangleROI'; }
    constructor(toolProps = {}, defaultToolProps = {
        supportedInteractionTypes: ['Mouse', 'Touch'],
        configuration: {
            storePointData: true,
            shadow: true,
            preventHandleOutsideImage: false,
            calculateStats: true,
            getTextLines: defaultGetTextLines,
            statsCalculator: BasicStatsCalculator,
        },
    }) {
        super(toolProps, defaultToolProps);
        this.addNewAnnotation = (evt) => {
            const eventDetail = evt.detail;
            const { currentPoints, element } = eventDetail;
            const worldPos = currentPoints.world;
            const enabledElement = getEnabledElement(element);
            const { viewport } = enabledElement;
            this.isDrawing = true;
            const annotation = (this.constructor).createAnnotationForViewport(viewport, {
                data: {
                    handles: {
                        points: [
                            [...worldPos],
                            [...worldPos],
                            [...worldPos],
                            [...worldPos],
                        ],
                        textBox: {
                            hasMoved: false,
                            worldPosition: [0, 0, 0],
                            worldBoundingBox: {
                                topLeft: [0, 0, 0],
                                topRight: [0, 0, 0],
                                bottomLeft: [0, 0, 0],
                                bottomRight: [0, 0, 0],
                            },
                        },
                    },
                    cachedStats: {},
                },
            });
            addAnnotation(annotation, element);
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.editData = {
                annotation,
                viewportIdsToRender,
                handleIndex: 3,
                movingTextBox: false,
                newAnnotation: true,
                hasMoved: false,
            };
            this._activateDraw(element);
            hideElementCursor(element);
            evt.preventDefault();
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            return annotation;
        };
        this._addNewAnnotationFromIndex = (element, idxPos, neg = false, SegmentNumber, segmentationId) => {
            const enabledElement = getEnabledElement(element);
            const { viewport, renderingEngine } = enabledElement;
        
            const tl = viewport.getImageData().imageData.indexToWorld(idxPos[0])
            const tr = viewport.getImageData().imageData.indexToWorld([idxPos[1][0],idxPos[0][1],idxPos[0][2]])
            const bl = viewport.getImageData().imageData.indexToWorld([idxPos[0][0],idxPos[1][1],idxPos[0][2]])
            const br = viewport.getImageData().imageData.indexToWorld(idxPos[1])
            
            const annotation = (this.constructor).createAnnotation({ metadata: viewport.getViewReference({sliceIndex: idxPos[0][2]}) }, {
                data: {
                    handles: {
                        points: [
                            [...tl],
                            [...tr],
                            [...bl],
                            [...br],
                        ],
                        textBox: {
                            hasMoved: false,
                            worldPosition: [0, 0, 0],
                            worldBoundingBox: {
                                topLeft: [0, 0, 0],
                                topRight: [0, 0, 0],
                                bottomLeft: [0, 0, 0],
                                bottomRight: [0, 0, 0],
                            },
                        },
                    },
                    cachedStats: {[this.getTargetId(viewport)]: {}},
                },
            });
            annotation.metadata.neg = neg;
            annotation.metadata.SegmentNumber = SegmentNumber;
            annotation.metadata.segmentationId = segmentationId;
            annotation.metadata.toolLoad = true;
            const { viewPlaneNormal, viewUp } = viewport.getCamera();
            this._calculateCachedStats(annotation, viewPlaneNormal, viewUp, renderingEngine, enabledElement);
            addAnnotation(annotation, element);
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.editData = {
                annotation,
                viewportIdsToRender,
                handleIndex: 3,
                movingTextBox: false,
                newAnnotation: true,
                hasMoved: false,
            };
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            return annotation;
        }
        this.isPointNearTool = (element, annotation, canvasCoords, proximity) => {
            const enabledElement = getEnabledElement(element);
            const { viewport } = enabledElement;
            const { data } = annotation;
            const { points } = data.handles;
            const canvasPoint1 = viewport.worldToCanvas(points[0]);
            const canvasPoint2 = viewport.worldToCanvas(points[3]);
            const rect = this._getRectangleImageCoordinates([
                canvasPoint1,
                canvasPoint2,
            ]);
            const point = [canvasCoords[0], canvasCoords[1]];
            const { left, top, width, height } = rect;
            const distanceToPoint = rectangle.distanceToPoint([left, top, width, height], point);
            if (distanceToPoint <= proximity) {
                return true;
            }
            return false;
        };
        this.toolSelectedCallback = (evt, annotation) => {
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            annotation.highlighted = true;
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.editData = {
                annotation,
                viewportIdsToRender,
                movingTextBox: false,
            };
            this._activateModify(element);
            hideElementCursor(element);
            const enabledElement = getEnabledElement(element);
            const { renderingEngine } = enabledElement;
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            evt.preventDefault();
        };
        this.handleSelectedCallback = (evt, annotation, handle) => {
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            const { data } = annotation;
            annotation.highlighted = true;
            let movingTextBox = false;
            let handleIndex;
            if (handle.worldPosition) {
                movingTextBox = true;
            }
            else {
                handleIndex = data.handles.points.findIndex((p) => p === handle);
            }
            const viewportIdsToRender = getViewportIdsWithToolToRender(element, this.getToolName());
            this.editData = {
                annotation,
                viewportIdsToRender,
                handleIndex,
                movingTextBox,
            };
            this._activateModify(element);
            hideElementCursor(element);
            const enabledElement = getEnabledElement(element);
            const { renderingEngine } = enabledElement;
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            evt.preventDefault();
        };
        this._endCallback = (evt) => {
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            const { annotation, viewportIdsToRender, newAnnotation, hasMoved } = this.editData;
            const { data } = annotation;
            if (newAnnotation && !hasMoved) {
                return;
            }
            data.handles.activeHandleIndex = null;
            this._deactivateModify(element);
            this._deactivateDraw(element);
            resetElementCursor(element);
            this.doneEditMemo();
            this.editData = null;
            this.isDrawing = false;
            if (this.isHandleOutsideImage &&
                this.configuration.preventHandleOutsideImage) {
                removeAnnotation(annotation.annotationUID);
            }
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            if (newAnnotation) {
                triggerAnnotationCompleted(annotation);
            }
        };
        this._dragCallback = (evt) => {
            this.isDrawing = true;
            const eventDetail = evt.detail;
            const { element } = eventDetail;
            const { annotation, viewportIdsToRender, handleIndex, movingTextBox, newAnnotation, } = this.editData;
            this.createMemo(element, annotation, { newAnnotation });
            const { data } = annotation;
            if (movingTextBox) {
                const { deltaPoints } = eventDetail;
                const worldPosDelta = deltaPoints.world;
                const { textBox } = data.handles;
                const { worldPosition } = textBox;
                worldPosition[0] += worldPosDelta[0];
                worldPosition[1] += worldPosDelta[1];
                worldPosition[2] += worldPosDelta[2];
                textBox.hasMoved = true;
            }
            else if (handleIndex === undefined) {
                const { deltaPoints } = eventDetail;
                const worldPosDelta = deltaPoints.world;
                const { points } = data.handles;
                points.forEach((point) => {
                    point[0] += worldPosDelta[0];
                    point[1] += worldPosDelta[1];
                    point[2] += worldPosDelta[2];
                });
                annotation.invalidated = true;
            }
            else {
                const { currentPoints } = eventDetail;
                const enabledElement = getEnabledElement(element);
                const { worldToCanvas, canvasToWorld } = enabledElement.viewport;
                const worldPos = currentPoints.world;
                const { points } = data.handles;
                points[handleIndex] = [...worldPos];
                let bottomLeftCanvas;
                let bottomRightCanvas;
                let topLeftCanvas;
                let topRightCanvas;
                let bottomLeftWorld;
                let bottomRightWorld;
                let topLeftWorld;
                let topRightWorld;
                switch (handleIndex) {
                    case 0:
                    case 3:
                        bottomLeftCanvas = worldToCanvas(points[0]);
                        topRightCanvas = worldToCanvas(points[3]);
                        bottomRightCanvas = [topRightCanvas[0], bottomLeftCanvas[1]];
                        topLeftCanvas = [bottomLeftCanvas[0], topRightCanvas[1]];
                        bottomRightWorld = canvasToWorld(bottomRightCanvas);
                        topLeftWorld = canvasToWorld(topLeftCanvas);
                        points[1] = bottomRightWorld;
                        points[2] = topLeftWorld;
                        break;
                    case 1:
                    case 2:
                        bottomRightCanvas = worldToCanvas(points[1]);
                        topLeftCanvas = worldToCanvas(points[2]);
                        bottomLeftCanvas = [
                            topLeftCanvas[0],
                            bottomRightCanvas[1],
                        ];
                        topRightCanvas = [
                            bottomRightCanvas[0],
                            topLeftCanvas[1],
                        ];
                        bottomLeftWorld = canvasToWorld(bottomLeftCanvas);
                        topRightWorld = canvasToWorld(topRightCanvas);
                        points[0] = bottomLeftWorld;
                        points[3] = topRightWorld;
                        break;
                }
                annotation.invalidated = true;
            }
            this.editData.hasMoved = true;
            const enabledElement = getEnabledElement(element);
            triggerAnnotationRenderForViewportIds(viewportIdsToRender);
            if (annotation.invalidated) {
                triggerAnnotationModified(annotation, element, ChangeTypes.HandlesUpdated);
            }
        };
        this.cancel = (element) => {
            if (this.isDrawing) {
                this.isDrawing = false;
                this._deactivateDraw(element);
                this._deactivateModify(element);
                resetElementCursor(element);
                const { annotation, viewportIdsToRender, newAnnotation } = this.editData;
                const { data } = annotation;
                annotation.highlighted = false;
                data.handles.activeHandleIndex = null;
                triggerAnnotationRenderForViewportIds(viewportIdsToRender);
                if (newAnnotation) {
                    triggerAnnotationCompleted(annotation);
                }
                this.editData = null;
                return annotation.annotationUID;
            }
        };
        this._activateDraw = (element) => {
            state.isInteractingWithTool = true;
            element.addEventListener(Events.MOUSE_UP, this._endCallback);
            element.addEventListener(Events.MOUSE_DRAG, this._dragCallback);
            element.addEventListener(Events.MOUSE_MOVE, this._dragCallback);
            element.addEventListener(Events.MOUSE_CLICK, this._endCallback);
            element.addEventListener(Events.TOUCH_END, this._endCallback);
            element.addEventListener(Events.TOUCH_DRAG, this._dragCallback);
            element.addEventListener(Events.TOUCH_TAP, this._endCallback);
        };
        this._deactivateDraw = (element) => {
            state.isInteractingWithTool = false;
            element.removeEventListener(Events.MOUSE_UP, this._endCallback);
            element.removeEventListener(Events.MOUSE_DRAG, this._dragCallback);
            element.removeEventListener(Events.MOUSE_MOVE, this._dragCallback);
            element.removeEventListener(Events.MOUSE_CLICK, this._endCallback);
            element.removeEventListener(Events.TOUCH_END, this._endCallback);
            element.removeEventListener(Events.TOUCH_DRAG, this._dragCallback);
            element.removeEventListener(Events.TOUCH_TAP, this._endCallback);
        };
        this._activateModify = (element) => {
            state.isInteractingWithTool = true;
            element.addEventListener(Events.MOUSE_UP, this._endCallback);
            element.addEventListener(Events.MOUSE_DRAG, this._dragCallback);
            element.addEventListener(Events.MOUSE_CLICK, this._endCallback);
            element.addEventListener(Events.TOUCH_END, this._endCallback);
            element.addEventListener(Events.TOUCH_DRAG, this._dragCallback);
            element.addEventListener(Events.TOUCH_TAP, this._endCallback);
        };
        this._deactivateModify = (element) => {
            state.isInteractingWithTool = false;
            element.removeEventListener(Events.MOUSE_UP, this._endCallback);
            element.removeEventListener(Events.MOUSE_DRAG, this._dragCallback);
            element.removeEventListener(Events.MOUSE_CLICK, this._endCallback);
            element.removeEventListener(Events.TOUCH_END, this._endCallback);
            element.removeEventListener(Events.TOUCH_DRAG, this._dragCallback);
            element.removeEventListener(Events.TOUCH_TAP, this._endCallback);
        };
        this.renderAnnotation = (enabledElement, svgDrawingHelper) => {
            let renderStatus = false;
            const { viewport } = enabledElement;
            const { element } = viewport;
            let annotations = getAnnotations(this.getToolName(), element);
            if (!annotations?.length) {
                return renderStatus;
            }
            annotations = this.filterInteractableAnnotationsForElement(element, annotations);
            if (!annotations?.length) {
                return renderStatus;
            }
            const targetId = this.getTargetId(viewport);
            const renderingEngine = viewport.getRenderingEngine();
            const styleSpecifier = {
                toolGroupId: this.toolGroupId,
                toolName: this.getToolName(),
                viewportId: enabledElement.viewport.id,
            };
            for (let i = 0; i < annotations.length; i++) {
                const annotation = annotations[i];
                const { annotationUID, data } = annotation;
                const { points, activeHandleIndex } = data.handles;
                const canvasCoordinates = points.map((p) => viewport.worldToCanvas(p));
                styleSpecifier.annotationUID = annotationUID;
                const { color, lineWidth, lineDash } = this.getAnnotationStyle({
                    annotation,
                    styleSpecifier,
                });
                const { viewPlaneNormal, viewUp } = viewport.getCamera();
                if (!data.cachedStats[targetId] ||
                    data.cachedStats[targetId].areaUnit == null) {
                    data.cachedStats[targetId] = {
                        Modality: null,
                        area: null,
                        max: null,
                        mean: null,
                        stdDev: null,
                        areaUnit: null,
                    };
                    this._calculateCachedStats(annotation, viewPlaneNormal, viewUp, renderingEngine, enabledElement);
                }
                else if (annotation.invalidated) {
                    this._throttledCalculateCachedStats(annotation, viewPlaneNormal, viewUp, renderingEngine, enabledElement);
                    if (viewport instanceof VolumeViewport) {
                        const { referencedImageId } = annotation.metadata;
                        for (const targetId in data.cachedStats) {
                            if (targetId.startsWith('imageId')) {
                                const viewports = renderingEngine.getStackViewports();
                                const invalidatedStack = viewports.find((vp) => {
                                    const referencedImageURI = csUtils.imageIdToURI(referencedImageId);
                                    const hasImageURI = vp.hasImageURI(referencedImageURI);
                                    const currentImageURI = csUtils.imageIdToURI(vp.getCurrentImageId());
                                    return hasImageURI && currentImageURI !== referencedImageURI;
                                });
                                if (invalidatedStack) {
                                    delete data.cachedStats[targetId];
                                }
                            }
                        }
                    }
                }
                if (!viewport.getRenderingEngine()) {
                    console.warn('Rendering Engine has been destroyed');
                    return renderStatus;
                }
                let activeHandleCanvasCoords;
                if (!isAnnotationVisible(annotationUID)) {
                    continue;
                }
                if (!isAnnotationLocked(annotationUID) &&
                    !this.editData &&
                    activeHandleIndex !== null) {
                    activeHandleCanvasCoords = [canvasCoordinates[activeHandleIndex]];
                }
                if (activeHandleCanvasCoords) {
                    const handleGroupUID = '0';
                    drawHandlesSvg(svgDrawingHelper, annotationUID, handleGroupUID, activeHandleCanvasCoords, {
                        color,
                    });
                }
                const dataId = `${annotationUID}-rect`;
                const rectangleUID = '0';
                drawRectSvg(svgDrawingHelper, annotationUID, rectangleUID, canvasCoordinates, {
                    color,
                    lineDash,
                    lineWidth,
                }, dataId);
                renderStatus = true;
                const options = this.getLinkedTextBoxStyle(styleSpecifier, annotation);
                 // Do not render text box for now
                 options.visibility = false;
                if (!options.visibility) {
                    data.handles.textBox = {
                        hasMoved: false,
                        worldPosition: [0, 0, 0],
                        worldBoundingBox: {
                            topLeft: [0, 0, 0],
                            topRight: [0, 0, 0],
                            bottomLeft: [0, 0, 0],
                            bottomRight: [0, 0, 0],
                        },
                    };
                    continue;
                }
                const textLines = this.configuration.getTextLines(data, targetId);
                if (!textLines || textLines.length === 0) {
                    continue;
                }
                if (!data.handles.textBox.hasMoved) {
                    const canvasTextBoxCoords = getTextBoxCoordsCanvas(canvasCoordinates);
                    data.handles.textBox.worldPosition =
                        viewport.canvasToWorld(canvasTextBoxCoords);
                }
                const textBoxPosition = viewport.worldToCanvas(data.handles.textBox.worldPosition);
                const textBoxUID = '1';
                const boundingBox = drawLinkedTextBoxSvg(svgDrawingHelper, annotationUID, textBoxUID, textLines, textBoxPosition, canvasCoordinates, {}, options);
                const { x: left, y: top, width, height } = boundingBox;
                data.handles.textBox.worldBoundingBox = {
                    topLeft: viewport.canvasToWorld([left, top]),
                    topRight: viewport.canvasToWorld([left + width, top]),
                    bottomLeft: viewport.canvasToWorld([left, top + height]),
                    bottomRight: viewport.canvasToWorld([left + width, top + height]),
                };
            }
            return renderStatus;
        };
        this._getRectangleImageCoordinates = (points) => {
            const [point0, point1] = points;
            return {
                left: Math.min(point0[0], point1[0]),
                top: Math.min(point0[1], point1[1]),
                width: Math.abs(point0[0] - point1[0]),
                height: Math.abs(point0[1] - point1[1]),
            };
        };
        this._calculateCachedStats = (annotation, viewPlaneNormal, viewUp, renderingEngine, enabledElement) => {
            if (!this.configuration.calculateStats) {
                return;
            }
            const { data } = annotation;
            const { viewport } = enabledElement;
            const { element } = viewport;
            const worldPos1 = data.handles.points[0];
            const worldPos2 = data.handles.points[3];
            const { cachedStats } = data;
            const targetIds = Object.keys(cachedStats);
            for (let i = 0; i < targetIds.length; i++) {
                const targetId = targetIds[i];
                const image = this.getTargetImageData(targetId);
                if (!image) {
                    continue;
                }
                const { dimensions, imageData, metadata, voxelManager } = image;

                let sliceIndex = 0
                if (targetId.startsWith('imageId:') || targetId.startsWith('volumeId:')) {
                    sliceIndex = viewport.getCurrentImageIdIndex();
                    dimensions[2]= sliceIndex+1
                }

                const pos1Index = transformWorldToIndex(imageData, worldPos1);
                pos1Index[0] = Math.floor(pos1Index[0]);
                pos1Index[1] = Math.floor(pos1Index[1]);
                pos1Index[2] = Math.floor(pos1Index[2]);
                const pos2Index = transformWorldToIndex(imageData, worldPos2);
                pos2Index[0] = Math.floor(pos2Index[0]);
                pos2Index[1] = Math.floor(pos2Index[1]);
                pos2Index[2] = Math.floor(pos2Index[2]);
                if (this._isInsideVolume(pos1Index, pos2Index, dimensions)) {
                    this.isHandleOutsideImage = false;
                    const iMin = Math.min(pos1Index[0], pos2Index[0]);
                    const iMax = Math.max(pos1Index[0], pos2Index[0]);
                    const jMin = Math.min(pos1Index[1], pos2Index[1]);
                    const jMax = Math.max(pos1Index[1], pos2Index[1]);
                    const kMin = Math.min(pos1Index[2], pos2Index[2]);
                    const kMax = Math.max(pos1Index[2], pos2Index[2]);
                    const boundsIJK = [
                        [iMin, iMax],
                        [jMin, jMax],
                        [kMin, kMax],
                    ];
                    const { worldWidth, worldHeight } = getWorldWidthAndHeightFromCorners(viewPlaneNormal, viewUp, worldPos1, worldPos2);
                    const handles = [pos1Index, pos2Index];
                    const { scale, areaUnit } = getCalibratedLengthUnitsAndScale(image, handles);
                    const area = Math.abs(worldWidth * worldHeight) / (scale * scale);
                    const pixelUnitsOptions = {
                        isPreScaled: isViewportPreScaled(viewport, targetId),
                        isSuvScaled: this.isSuvScaled(viewport, targetId, annotation.metadata.referencedImageId),
                    };
                    const modalityUnit = getPixelValueUnits(metadata.Modality, annotation.metadata.referencedImageId, pixelUnitsOptions);
                    let pointsInShape = voxelManager.forEach(this.configuration.statsCalculator.statsCallback, {
                        boundsIJK,
                        imageData,
                        returnPoints: this.configuration.storePointData,
                    });
                    if (targetId.startsWith('imageId:')){
                        pointsInShape.forEach(element => {
                            element.pointIJK[2]=sliceIndex                        
                        });
                    }
                    else if (targetId.startsWith('volumeId:')){
                        const axialViewport = services.cornerstoneViewportService.getCornerstoneViewport('mpr-axial') 
                            || services.cornerstoneViewportService.getCornerstoneViewport('default');
                        if (!axialViewport) {
                            continue;
                        }
                        const imageIdsInVolume = axialViewport.getImageIds();
                        if (!imageIdsInVolume?.length) {
                            continue;
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
                            pointsInShape.forEach(element => {
                                element.pointIJK[2] = imageIdsLength - Math.round(element.pointIJK[2]) - 1;
                            });
                        }
                    }
                    const stats = this.configuration.statsCalculator.getStatistics();
                    cachedStats[targetId] = {
                        Modality: metadata.Modality,
                        area,
                        mean: stats.mean?.value,
                        stdDev: stats.stdDev?.value,
                        max: stats.max?.value,
                        statsArray: stats.array,
                        pointsInShape: pointsInShape,
                        areaUnit,
                        modalityUnit,
                    };
                }
                else {
                    this.isHandleOutsideImage = true;
                    let pointsInShape = [];
                    pointsInShape.push({pointIJK: pos1Index});
                    pointsInShape.push({pointIJK: pos2Index});
                    cachedStats[targetId] = {
                        Modality: metadata.Modality,
                        pointsInShape: pointsInShape,
                    };
                }
            }
            const invalidated = annotation.invalidated;
            annotation.invalidated = false;
            if (invalidated) {
                triggerAnnotationModified(annotation, element, ChangeTypes.StatsUpdated);
            }
            return cachedStats;
        };
        this._isInsideVolume = (index1, index2, dimensions) => {
            return (csUtils.indexWithinDimensions(index1, dimensions) &&
                csUtils.indexWithinDimensions(index2, dimensions));
        };
        this._throttledCalculateCachedStats = throttle(this._calculateCachedStats, 100, { trailing: true });
    }
    static { this.hydrate = (viewportId, points, options) => {
        const enabledElement = getEnabledElementByViewportId(viewportId);
        if (!enabledElement) {
            return;
        }
        const { FrameOfReferenceUID, referencedImageId, viewPlaneNormal, instance, viewport, } = this.hydrateBase(RectangleROITool, enabledElement, points, options);
        const { toolInstance, ...serializableOptions } = options || {};
        const annotation = {
            annotationUID: options?.annotationUID || csUtils.uuidv4(),
            data: {
                handles: {
                    points,
                    activeHandleIndex: null,
                },
                label: '',
                cachedStats: {},
            },
            highlighted: false,
            autoGenerated: false,
            invalidated: false,
            isLocked: false,
            isVisible: true,
            metadata: {
                toolName: instance.getToolName(),
                viewPlaneNormal,
                FrameOfReferenceUID,
                referencedImageId,
                ...serializableOptions,
            },
        };
        addAnnotation(annotation, viewport.element);
        triggerAnnotationRenderForViewportIds([viewport.id]);
    }; }
}
function defaultGetTextLines(data, targetId) {
    const cachedVolumeStats = data.cachedStats[targetId];
    const { area, mean, max, stdDev, areaUnit, modalityUnit } = cachedVolumeStats;
    if (mean === undefined || mean === null) {
        return;
    }
    const textLines = [];
    textLines.push(`Area: ${csUtils.roundNumber(area)} ${areaUnit}`);
    textLines.push(`Mean: ${csUtils.roundNumber(mean)} ${modalityUnit}`);
    textLines.push(`Max: ${csUtils.roundNumber(max)} ${modalityUnit}`);
    textLines.push(`Std Dev: ${csUtils.roundNumber(stdDev)} ${modalityUnit}`);
    return textLines;
}
export default RectangleROITool;
