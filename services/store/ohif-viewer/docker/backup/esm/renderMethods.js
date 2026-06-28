import { drawHandles as drawHandlesSvg, drawPolyline as drawPolylineSvg, drawPath as drawPathSvg, } from '../../../drawingSvg';
import { polyline } from '../../../utilities/math';
import { findOpenUShapedContourVectorToPeakOnRender } from './findOpenUShapedContourVectorToPeak';
import getContourHolesDataCanvas from '../../../utilities/contours/getContourHolesDataCanvas';
const { pointsAreWithinCloseContourProximity } = polyline;
function _getRenderingOptions(enabledElement, annotation) {
    const styleSpecifier = {
        toolGroupId: this.toolGroupId,
        toolName: this.getToolName(),
        viewportId: enabledElement.viewport.id,
        annotationUID: annotation.annotationUID,
    };
    const { lineWidth, lineDash, color, fillColor, fillOpacity } = this.getAnnotationStyle({
        annotation,
        styleSpecifier,
    });
    const { closed: isClosedContour } = annotation.data.contour;
    const options = {
        color,
        width: lineWidth,
        lineDash,
        fillColor,
        fillOpacity,
        closePath: isClosedContour,
    };
    return options;
}
function renderContour(enabledElement, svgDrawingHelper, annotation) {
    if (!enabledElement?.viewport?.getImageData()) {
        return;
    }
    if (annotation.data.contour.closed) {
        this.renderClosedContour(enabledElement, svgDrawingHelper, annotation);
    }
    else {
        if (annotation.data.isOpenUShapeContour) {
            calculateUShapeContourVectorToPeakIfNotPresent(enabledElement, annotation);
            this.renderOpenUShapedContour(enabledElement, svgDrawingHelper, annotation);
        }
        else {
            this.renderOpenContour(enabledElement, svgDrawingHelper, annotation);
        }
    }
}
function calculateUShapeContourVectorToPeakIfNotPresent(enabledElement, annotation) {
    if (!annotation.data.openUShapeContourVectorToPeak) {
        annotation.data.openUShapeContourVectorToPeak =
            findOpenUShapedContourVectorToPeakOnRender(enabledElement, annotation);
    }
}
function renderClosedContour(enabledElement, svgDrawingHelper, annotation) {
    if (annotation.parentAnnotationUID) {
        return;
    }
    const { viewport } = enabledElement;
    const options = this._getRenderingOptions(enabledElement, annotation);
    const canvasPolyline = annotation.data.contour.polyline.map((worldPos) => viewport.worldToCanvas(worldPos));
    const childContours = getContourHolesDataCanvas(annotation, viewport);
    const allContours = [canvasPolyline, ...childContours];
    const polylineUID = '1';
    drawPathSvg(svgDrawingHelper, annotation.annotationUID, polylineUID, allContours, options);
}
function renderOpenContour(enabledElement, svgDrawingHelper, annotation) {
    const { viewport } = enabledElement;
    const options = this._getRenderingOptions(enabledElement, annotation);
    options.width = 2;
    const canvasPoints = annotation.data.contour.polyline.map((worldPos) => viewport.worldToCanvas(worldPos));
    const polylineUID = '1';
    drawPolylineSvg(svgDrawingHelper, annotation.annotationUID, polylineUID, canvasPoints, options);
    const activeHandleIndex = annotation.data.handles.activeHandleIndex;
    if (this.configuration.alwaysRenderOpenContourHandles?.enabled === true) {
        const radius = this.configuration.alwaysRenderOpenContourHandles.radius;
        const handleGroupUID = '0';
        const handlePoints = [
            canvasPoints[0],
            canvasPoints[canvasPoints.length - 1],
        ];
        if (activeHandleIndex === 0) {
            handlePoints.shift();
        }
        else if (activeHandleIndex === 1) {
            handlePoints.pop();
        }
        drawHandlesSvg(svgDrawingHelper, annotation.annotationUID, handleGroupUID, handlePoints, {
            color: options.color,
            handleRadius: radius,
        });
    }
    if (activeHandleIndex !== null) {
        const handleGroupUID = '1';
        const indexOfCanvasPoints = activeHandleIndex === 0 ? 0 : canvasPoints.length - 1;
        const handlePoint = canvasPoints[indexOfCanvasPoints];
        drawHandlesSvg(svgDrawingHelper, annotation.annotationUID, handleGroupUID, [handlePoint], { color: options.color });
    }
}
function renderOpenUShapedContour(enabledElement, svgDrawingHelper, annotation) {
    const { viewport } = enabledElement;
    const { openUShapeContourVectorToPeak } = annotation.data;
    const { polyline } = annotation.data.contour;
    this.renderOpenContour(enabledElement, svgDrawingHelper, annotation);
    if (!openUShapeContourVectorToPeak) {
        return;
    }
    const firstCanvasPoint = viewport.worldToCanvas(polyline[0]);
    const lastCanvasPoint = viewport.worldToCanvas(polyline[polyline.length - 1]);
    const openUShapeContourVectorToPeakCanvas = [
        viewport.worldToCanvas(openUShapeContourVectorToPeak[0]),
        viewport.worldToCanvas(openUShapeContourVectorToPeak[1]),
    ];
    const options = this._getRenderingOptions(enabledElement, annotation);
    drawPolylineSvg(svgDrawingHelper, annotation.annotationUID, 'first-to-last', [firstCanvasPoint, lastCanvasPoint], {
        color: options.color,
        width: options.width,
        closePath: false,
        lineDash: '2,2',
    });
    drawPolylineSvg(svgDrawingHelper, annotation.annotationUID, 'midpoint-to-open-contour', [
        openUShapeContourVectorToPeakCanvas[0],
        openUShapeContourVectorToPeakCanvas[1],
    ], {
        color: options.color,
        width: options.width,
        closePath: false,
        lineDash: '2,2',
    });
}
function renderContourBeingDrawn(enabledElement, svgDrawingHelper, annotation) {
    const options = this._getRenderingOptions(enabledElement, annotation);
    const { allowOpenContours } = this.configuration;
    const { canvasPoints } = this.drawData;
    options.closePath = false;
    drawPolylineSvg(svgDrawingHelper, annotation.annotationUID, '1', canvasPoints, options);
    if (allowOpenContours) {
        const firstPoint = canvasPoints[0];
        const lastPoint = canvasPoints[canvasPoints.length - 1];
        if (pointsAreWithinCloseContourProximity(firstPoint, lastPoint, this.configuration.closeContourProximity)) {
            drawPolylineSvg(svgDrawingHelper, annotation.annotationUID, '2', [lastPoint, firstPoint], options);
        }
        else {
            const handleGroupUID = '0';
            drawHandlesSvg(svgDrawingHelper, annotation.annotationUID, handleGroupUID, [firstPoint], { color: options.color, handleRadius: 2 });
        }
    }
}
function renderClosedContourBeingEdited(enabledElement, svgDrawingHelper, annotation) {
    const { viewport } = enabledElement;
    const { fusedCanvasPoints } = this.editData;
    if (fusedCanvasPoints === undefined) {
        this.renderClosedContour(enabledElement, svgDrawingHelper, annotation);
        return;
    }
    const childContours = getContourHolesDataCanvas(annotation, viewport);
    const allContours = [fusedCanvasPoints, ...childContours];
    const options = this._getRenderingOptions(enabledElement, annotation);
    const polylineUIDToRender = 'preview-1';
    if (annotation.parentAnnotationUID && options.fillOpacity) {
        options.fillOpacity = 0;
    }
    drawPathSvg(svgDrawingHelper, annotation.annotationUID, polylineUIDToRender, allContours, options);
}
function renderOpenContourBeingEdited(enabledElement, svgDrawingHelper, annotation) {
    const { fusedCanvasPoints } = this.editData;
    if (fusedCanvasPoints === undefined) {
        this.renderOpenContour(enabledElement, svgDrawingHelper, annotation);
        return;
    }
    const options = this._getRenderingOptions(enabledElement, annotation);
    const polylineUIDToRender = 'preview-1';
    drawPolylineSvg(svgDrawingHelper, annotation.annotationUID, polylineUIDToRender, fusedCanvasPoints, options);
}
function renderPointContourWithMarker(enabledElement, svgDrawingHelper, annotation) {
    if (annotation.parentAnnotationUID) {
        return;
    }
    const { viewport } = enabledElement;
    const options = this._getRenderingOptions(enabledElement, annotation);
    const canvasPolyline = annotation.data.contour.polyline.map((worldPos) => viewport.worldToCanvas(worldPos));
    const childContours = getContourHolesDataCanvas(annotation, viewport);
    const polylineUID = '1';
    const center = canvasPolyline[0];
    const radius = 6;
    const numberOfPoints = 100;
    const circlePoints = [];
    for (let i = 0; i < numberOfPoints; i++) {
        const angle = (i / numberOfPoints) * 2 * Math.PI;
        const x = center[0] + radius * Math.cos(angle);
        const y = center[1] + radius * Math.sin(angle);
        circlePoints.push([x, y]);
    }
    const crosshair = [
        [center[0] - radius * 2, center[1]],
        [center[0] + radius * 2, center[1]],
        [center[0], center[1] - radius * 2],
        [center[0], center[1] + radius * 2],
    ];
    drawPathSvg(svgDrawingHelper, annotation.annotationUID, polylineUID + '-crosshair_v', [crosshair[0], crosshair[1]], options);
    drawPathSvg(svgDrawingHelper, annotation.annotationUID, polylineUID + '-crosshair_h', [crosshair[2], crosshair[3]], options);
    const allContours = [circlePoints, ...childContours];
    drawPathSvg(svgDrawingHelper, annotation.annotationUID, polylineUID, allContours, options);
}
function registerRenderMethods(toolInstance) {
    toolInstance.renderContour = renderContour.bind(toolInstance);
    toolInstance.renderClosedContour = renderClosedContour.bind(toolInstance);
    toolInstance.renderOpenContour = renderOpenContour.bind(toolInstance);
    toolInstance.renderPointContourWithMarker =
        renderPointContourWithMarker.bind(toolInstance);
    toolInstance.renderOpenUShapedContour =
        renderOpenUShapedContour.bind(toolInstance);
    toolInstance.renderContourBeingDrawn =
        renderContourBeingDrawn.bind(toolInstance);
    toolInstance.renderClosedContourBeingEdited =
        renderClosedContourBeingEdited.bind(toolInstance);
    toolInstance.renderOpenContourBeingEdited =
        renderOpenContourBeingEdited.bind(toolInstance);
    toolInstance._getRenderingOptions = _getRenderingOptions.bind(toolInstance);
}
export default registerRenderMethods;
