import { BaseVolumeViewport, cache, getEnabledElement, metaData, utilities as csUtils, StackViewport, } from '@cornerstonejs/core';
import { vec2 } from 'gl-matrix';
import AnnotationDisplayTool from './AnnotationDisplayTool';
import { isAnnotationLocked } from '../../stateManagement/annotation/annotationLocking';
import { isAnnotationVisible } from '../../stateManagement/annotation/annotationVisibility';
import { addAnnotation, removeAnnotation, getAnnotation, } from '../../stateManagement/annotation/annotationState';
import { triggerAnnotationModified } from '../../stateManagement/annotation/helpers/state';
import ChangeTypes from '../../enums/ChangeTypes';
import { setAnnotationSelected } from '../../stateManagement/annotation/annotationSelection';
import { addContourSegmentationAnnotation } from '../../utilities/contourSegmentation';
const { DefaultHistoryMemo } = csUtils.HistoryMemo;
const { PointsManager } = csUtils;
class AnnotationTool extends AnnotationDisplayTool {
    static createAnnotation(...annotationBaseData) {
        let annotation = {
            annotationUID: null,
            highlighted: true,
            invalidated: true,
            metadata: {
                toolName: this.toolName,
            },
            data: {
                text: '',
                handles: {
                    points: new Array(),
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
                label: '',
            },
        };
        for (const baseData of annotationBaseData) {
            annotation = csUtils.deepMerge(annotation, baseData);
        }
        return annotation;
    }
    static createAnnotationForViewport(viewport, ...annotationBaseData) {
        return this.createAnnotation({ metadata: viewport.getViewReference() }, ...annotationBaseData);
    }
    static createAndAddAnnotation(viewport, ...annotationBaseData) {
        const annotation = this.createAnnotationForViewport(viewport, ...annotationBaseData);
        addAnnotation(annotation, viewport.element);
        triggerAnnotationModified(annotation, viewport.element);
    }
    constructor(toolProps, defaultToolProps) {
        super(toolProps, defaultToolProps);
        this.mouseMoveCallback = (evt, filteredAnnotations) => {
            if (!filteredAnnotations) {
                return false;
            }
            const { element, currentPoints } = evt.detail;
            const canvasCoords = currentPoints.canvas;
            let annotationsNeedToBeRedrawn = false;
            for (const annotation of filteredAnnotations) {
                if (isAnnotationLocked(annotation.annotationUID) ||
                    !isAnnotationVisible(annotation.annotationUID)) {
                    continue;
                }
                const { data } = annotation;
                const activateHandleIndex = data.handles
                    ? data.handles.activeHandleIndex
                    : undefined;
                const near = this._imagePointNearToolOrHandle(element, annotation, canvasCoords, 6);
                const nearToolAndNotMarkedActive = near && !annotation.highlighted;
                const notNearToolAndMarkedActive = !near && annotation.highlighted;
                if (nearToolAndNotMarkedActive || notNearToolAndMarkedActive) {
                    annotation.highlighted = !annotation.highlighted;
                    annotationsNeedToBeRedrawn = true;
                }
                else if (data.handles &&
                    data.handles.activeHandleIndex !== activateHandleIndex) {
                    annotationsNeedToBeRedrawn = true;
                }
            }
            return annotationsNeedToBeRedrawn;
        };
        this.isSuvScaled = AnnotationTool.isSuvScaled;
        if (toolProps.configuration?.getTextLines) {
            this.configuration.getTextLines = toolProps.configuration.getTextLines;
        }
        if (toolProps.configuration?.statsCalculator) {
            this.configuration.statsCalculator =
                toolProps.configuration.statsCalculator;
        }
    }
    getHandleNearImagePoint(element, annotation, canvasCoords, proximity) {
        const enabledElement = getEnabledElement(element);
        const { viewport } = enabledElement;
        const { data } = annotation;
        const { isCanvasAnnotation } = data;
        const { points, textBox } = data.handles;
        if (textBox) {
            const { worldBoundingBox } = textBox;
            if (worldBoundingBox) {
                const canvasBoundingBox = {
                    topLeft: viewport.worldToCanvas(worldBoundingBox.topLeft),
                    topRight: viewport.worldToCanvas(worldBoundingBox.topRight),
                    bottomLeft: viewport.worldToCanvas(worldBoundingBox.bottomLeft),
                    bottomRight: viewport.worldToCanvas(worldBoundingBox.bottomRight),
                };
                if (canvasCoords[0] >= canvasBoundingBox.topLeft[0] &&
                    canvasCoords[0] <= canvasBoundingBox.bottomRight[0] &&
                    canvasCoords[1] >= canvasBoundingBox.topLeft[1] &&
                    canvasCoords[1] <= canvasBoundingBox.bottomRight[1]) {
                    data.handles.activeHandleIndex = null;
                    return textBox;
                }
            }
        }
        for (let i = 0; i < points?.length; i++) {
            const point = points[i];
            const annotationCanvasCoordinate = isCanvasAnnotation
                ? point.slice(0, 2)
                : viewport.worldToCanvas(point);
            const near = vec2.distance(canvasCoords, annotationCanvasCoordinate) < proximity;
            if (near === true) {
                data.handles.activeHandleIndex = i;
                return point;
            }
        }
        data.handles.activeHandleIndex = null;
    }
    getLinkedTextBoxStyle(specifications, annotation) {
        return {
            visibility: this.getStyle('textBoxVisibility', specifications, annotation),
            fontFamily: this.getStyle('textBoxFontFamily', specifications, annotation),
            fontSize: this.getStyle('textBoxFontSize', specifications, annotation),
            color: this.getStyle('textBoxColor', specifications, annotation),
            shadow: this.getStyle('textBoxShadow', specifications, annotation),
            background: this.getStyle('textBoxBackground', specifications, annotation),
            lineWidth: this.getStyle('textBoxLinkLineWidth', specifications, annotation),
            lineDash: this.getStyle('textBoxLinkLineDash', specifications, annotation),
        };
    }
    static isSuvScaled(viewport, targetId, imageId) {
        if (viewport instanceof BaseVolumeViewport) {
            const volumeId = csUtils.getVolumeId(targetId);
            const volume = cache.getVolume(volumeId);
            return volume?.scaling?.PT !== undefined;
        }
        const scalingModule = imageId && metaData.get('scalingModule', imageId);
        return typeof scalingModule?.suvbw === 'number';
    }
    getAnnotationStyle(context) {
        const { annotation, styleSpecifier } = context;
        const getStyle = (property) => this.getStyle(property, styleSpecifier, annotation);
        const { annotationUID } = annotation;
        const visibility = isAnnotationVisible(annotationUID);
        const locked = isAnnotationLocked(annotationUID);
        const lineWidth = getStyle('lineWidth');
        const lineDash = getStyle('lineDash');
        const angleArcLineDash = getStyle('angleArcLineDash');
        let color = getStyle('color');
        if (annotation.metadata.neg === true) {
            color = 'rgb(255, 0, 0)';
        }
        const markerSize = getStyle('markerSize');
        const shadow = getStyle('shadow');
        const textboxStyle = this.getLinkedTextBoxStyle(styleSpecifier, annotation);
        return {
            visibility,
            locked,
            color,
            lineWidth,
            lineDash,
            lineOpacity: 1,
            fillColor: color,
            fillOpacity: 0,
            shadow,
            textbox: textboxStyle,
            markerSize,
            angleArcLineDash,
        };
    }
    _imagePointNearToolOrHandle(element, annotation, canvasCoords, proximity) {
        const handleNearImagePoint = this.getHandleNearImagePoint(element, annotation, canvasCoords, proximity);
        if (handleNearImagePoint) {
            return true;
        }
        const toolNewImagePoint = this.isPointNearTool(element, annotation, canvasCoords, proximity, 'mouse');
        if (toolNewImagePoint) {
            return true;
        }
    }
    static createAnnotationState(annotation, deleting) {
        const { data, annotationUID } = annotation;
        const cloneData = {
            ...data,
            cachedStats: {},
        };
        delete cloneData.contour;
        delete cloneData.spline;
        const state = {
            annotationUID,
            data: structuredClone(cloneData),
            deleting,
        };
        const contour = data.contour;
        if (contour) {
            state.data.contour = {
                ...contour,
                polyline: null,
                pointsManager: PointsManager.create3(contour.polyline.length, contour.polyline),
            };
        }
        return state;
    }
    static createAnnotationMemo(element, annotation, options) {
        if (!annotation) {
            return;
        }
        const { newAnnotation, deleting = newAnnotation ? false : undefined } = options || {};
        const { annotationUID } = annotation;
        const state = AnnotationTool.createAnnotationState(annotation, deleting);
        const annotationMemo = {
            restoreMemo: () => {
                const newState = AnnotationTool.createAnnotationState(annotation, deleting);
                const { viewport } = getEnabledElement(element) || {};
                viewport?.setViewReference(annotation.metadata);
                if (state.deleting === true) {
                    state.deleting = false;
                    Object.assign(annotation.data, state.data);
                    if (annotation.data.contour) {
                        const annotationData = annotation.data;
                        annotationData.contour.polyline = state.data.contour.pointsManager.points;
                        delete state.data.contour.pointsManager;
                        if (annotationData.segmentation) {
                            addContourSegmentationAnnotation(annotation);
                        }
                    }
                    state.data = newState.data;
                    addAnnotation(annotation, element);
                    setAnnotationSelected(annotation.annotationUID, true);
                    viewport?.render();
                    return;
                }
                if (state.deleting === false) {
                    state.deleting = true;
                    state.data = newState.data;
                    setAnnotationSelected(annotation.annotationUID);
                    removeAnnotation(annotation.annotationUID);
                    viewport?.render();
                    return;
                }
                const currentAnnotation = getAnnotation(annotationUID);
                if (!currentAnnotation) {
                    console.warn('No current annotation');
                    return;
                }
                Object.assign(currentAnnotation.data, state.data);
                if (currentAnnotation.data.contour) {
                    currentAnnotation.data
                        .contour.polyline = state.data.contour.pointsManager.points;
                }
                state.data = newState.data;
                currentAnnotation.invalidated = true;
                triggerAnnotationModified(currentAnnotation, element, ChangeTypes.History);
            },
            id: annotationUID,
            operationType: 'annotation',
        };
        DefaultHistoryMemo.push(annotationMemo);
        return annotationMemo;
    }
    createMemo(element, annotation, options) {
        this.memo ||= AnnotationTool.createAnnotationMemo(element, annotation, options);
    }
    static hydrateBase(ToolClass, enabledElement, points, options = {}) {
        if (!enabledElement) {
            return null;
        }
        const { viewport } = enabledElement;
        const FrameOfReferenceUID = viewport.getFrameOfReferenceUID();
        const camera = viewport.getCamera();
        const viewPlaneNormal = options.viewplaneNormal ?? camera.viewPlaneNormal;
        const viewUp = options.viewUp ?? camera.viewUp;
        const instance = options.toolInstance || new ToolClass();
        let referencedImageId;
        let finalViewPlaneNormal = viewPlaneNormal;
        let finalViewUp = viewUp;
        if (options.referencedImageId) {
            referencedImageId = options.referencedImageId;
            finalViewPlaneNormal = undefined;
            finalViewUp = undefined;
        }
        else {
            if (viewport instanceof StackViewport) {
                const closestImageIndex = csUtils.getClosestStackImageIndexForPoint(points[0], viewport);
                if (closestImageIndex !== undefined) {
                    referencedImageId = viewport.getImageIds()[closestImageIndex];
                }
            }
            else if (viewport instanceof BaseVolumeViewport) {
                referencedImageId = instance.getReferencedImageId(viewport, points[0], viewPlaneNormal, viewUp);
            }
            else {
                throw new Error('Unsupported viewport type');
            }
        }
        return {
            FrameOfReferenceUID,
            referencedImageId,
            viewPlaneNormal: finalViewPlaneNormal,
            viewUp: finalViewUp,
            instance,
            viewport,
        };
    }
}
AnnotationTool.toolName = 'AnnotationTool';
export default AnnotationTool;
