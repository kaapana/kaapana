import { getEnabledElementByViewportId, VolumeViewport, cache, } from '@cornerstonejs/core';
import addLabelmapToElement from './addLabelmapToElement';
import removeLabelmapFromElement from './removeLabelmapFromElement';
import { getActiveSegmentation } from '../../../stateManagement/segmentation/activeSegmentation';
import { getColorLUT } from '../../../stateManagement/segmentation/getColorLUT';
import { getCurrentLabelmapImageIdsForViewport } from '../../../stateManagement/segmentation/getCurrentLabelmapImageIdForViewport';
import { getSegmentation } from '../../../stateManagement/segmentation/getSegmentation';
import { segmentationStyle } from '../../../stateManagement/segmentation/SegmentationStyle';
import SegmentationRepresentations from '../../../enums/SegmentationRepresentations';
import { internalGetHiddenSegmentIndices } from '../../../stateManagement/segmentation/helpers/internalGetHiddenSegmentIndices';
import { getActiveSegmentIndex } from '../../../stateManagement/segmentation/getActiveSegmentIndex';
import { getLabelmapActorEntries } from '../../../stateManagement/segmentation/helpers/getSegmentationActor';
import { getPolySeg } from '../../../config';
import { computeAndAddRepresentation } from '../../../utilities/segmentation/computeAndAddRepresentation';
import { triggerSegmentationDataModified } from '../../../stateManagement/segmentation/triggerSegmentationEvents';
import { defaultSegmentationStateManager } from '../../../stateManagement/segmentation/SegmentationStateManager';
export const MAX_NUMBER_COLORS = 255;
const labelMapConfigCache = new Map();
const stackAddLabelmapLastSlice = new Map();
let polySegConversionInProgress = false;
function removeRepresentation(viewportId, segmentationId, renderImmediate = false) {
    const enabledElement = getEnabledElementByViewportId(viewportId);
    stackAddLabelmapLastSlice.delete(`${viewportId}-${segmentationId}`);
    labelMapConfigCache.forEach((value, key) => {
        if (key.includes(segmentationId)) {
            labelMapConfigCache.delete(key);
        }
    });
    if (!enabledElement) {
        return;
    }
    const { viewport } = enabledElement;
    removeLabelmapFromElement(viewport.element, segmentationId);
    if (!renderImmediate) {
        return;
    }
    viewport.render();
}
async function render(viewport, representation) {
    const { segmentationId, config } = representation;
    const segmentation = getSegmentation(segmentationId);
    if (!segmentation) {
        console.warn('No segmentation found for segmentationId: ', segmentationId);
        return;
    }
    let labelmapData = segmentation.representationData[SegmentationRepresentations.Labelmap];
    let labelmapActorEntries = getLabelmapActorEntries(viewport.id, segmentationId);
    if (!labelmapData &&
        getPolySeg()?.canComputeRequestedRepresentation(segmentationId, SegmentationRepresentations.Labelmap) &&
        !polySegConversionInProgress) {
        polySegConversionInProgress = true;
        const polySeg = getPolySeg();
        labelmapData = await computeAndAddRepresentation(segmentationId, SegmentationRepresentations.Labelmap, () => polySeg.computeLabelmapData(segmentationId, { viewport }), () => null, () => {
            defaultSegmentationStateManager.processLabelmapRepresentationAddition(viewport.id, segmentationId);
            setTimeout(() => {
                triggerSegmentationDataModified(segmentationId);
            }, 0);
        });
        if (!labelmapData) {
            throw new Error(`No labelmap data found for segmentationId ${segmentationId}.`);
        }
        polySegConversionInProgress = false;
    }
    else if (!labelmapData && !getPolySeg()) {
        console.debug(`No labelmap data found for segmentationId ${segmentationId} and PolySeg add-on is not configured. Unable to convert from other representations to labelmap. Please register PolySeg using cornerstoneTools.init({ addons: { polySeg } }) to enable automatic conversion.`);
    }
    if (!labelmapData) {
        return;
    }
    if (viewport instanceof VolumeViewport) {
        if (!labelmapActorEntries?.length) {
            await _addLabelmapToViewport(viewport, labelmapData, segmentationId, config);
        }
        labelmapActorEntries = getLabelmapActorEntries(viewport.id, segmentationId);
    }
    else {
        const labelmapImageIds = getCurrentLabelmapImageIdsForViewport(viewport.id, segmentationId);
        if (!labelmapImageIds?.length) {
            return;
        }
        const currentImageId = viewport.getCurrentImageId();
        const sliceKey = `${viewport.id}-${segmentationId}`;
        const lastRunImageId = stackAddLabelmapLastSlice.get(sliceKey);
        const sliceChanged = lastRunImageId !== currentImageId;
        const suppressTriggerModificationEvents = labelmapActorEntries?.length > 0;
        if (sliceChanged) {
            stackAddLabelmapLastSlice.set(sliceKey, currentImageId);
            await _addLabelmapToViewport(viewport, labelmapData, segmentationId, config, suppressTriggerModificationEvents);
        }
        labelmapActorEntries = getLabelmapActorEntries(viewport.id, segmentationId);
    }
    if (!labelmapActorEntries?.length) {
        return;
    }
    for (const labelmapActorEntry of labelmapActorEntries) {
        _setLabelmapColorAndOpacity(viewport.id, labelmapActorEntry, representation);
    }
}
function _setLabelmapColorAndOpacity(viewportId, labelmapActorEntry, segmentationRepresentation) {
    const { segmentationId } = segmentationRepresentation;
    const { cfun, ofun } = segmentationRepresentation.config;
    const { colorLUTIndex } = segmentationRepresentation;
    const activeSegmentation = getActiveSegmentation(viewportId);
    const isActiveLabelmap = activeSegmentation?.segmentationId === segmentationId;
    const labelmapStyle = segmentationStyle.getStyle({
        viewportId,
        type: SegmentationRepresentations.Labelmap,
        segmentationId,
    });
    const renderInactiveSegmentations = segmentationStyle.getRenderInactiveSegmentations(viewportId);
    const colorLUT = getColorLUT(colorLUTIndex);
    const numColors = Math.min(256, colorLUT.length);
    const { outlineWidth, renderOutline, outlineOpacity, activeSegmentOutlineWidthDelta, } = _getLabelmapConfig(labelmapStyle, isActiveLabelmap);
    const segmentsHidden = internalGetHiddenSegmentIndices(viewportId, {
        segmentationId,
        type: SegmentationRepresentations.Labelmap,
    });
    for (let i = 0; i < numColors; i++) {
        const segmentIndex = i;
        const segmentColor = colorLUT[segmentIndex];
        const perSegmentStyle = segmentationStyle.getStyle({
            viewportId,
            type: SegmentationRepresentations.Labelmap,
            segmentationId,
            segmentIndex,
        });
        const segmentSpecificLabelmapConfig = perSegmentStyle;
        const { fillAlpha, outlineWidth, renderFill, renderOutline } = _getLabelmapConfig(labelmapStyle, isActiveLabelmap, segmentSpecificLabelmapConfig);
        const { forceOpacityUpdate, forceColorUpdate } = _needsTransferFunctionUpdate(viewportId, segmentationId, segmentIndex, {
            fillAlpha,
            renderFill,
            renderOutline,
            segmentColor,
            outlineWidth,
            segmentsHidden: segmentsHidden,
            cfun,
            ofun,
        });
        if (forceColorUpdate) {
            cfun.addRGBPoint(segmentIndex, segmentColor[0] / MAX_NUMBER_COLORS, segmentColor[1] / MAX_NUMBER_COLORS, segmentColor[2] / MAX_NUMBER_COLORS);
        }
        if (forceOpacityUpdate) {
            if (renderFill) {
                const segmentOpacity = segmentsHidden.has(segmentIndex)
                    ? 0
                    : (segmentColor[3] / 255) * fillAlpha;
                ofun.removePoint(segmentIndex);
                ofun.addPointLong(segmentIndex, segmentOpacity, 0.5, 1.0);
            }
            else {
                ofun.addPointLong(segmentIndex, 0.01, 0.5, 1.0);
            }
        }
    }
    ofun.setClamping(false);
    const labelmapActor = labelmapActorEntry.actor;
    const { preLoad } = labelmapActor.get?.('preLoad') || { preLoad: null };
    if (preLoad) {
        preLoad({ cfun, ofun, actor: labelmapActor });
    }
    else {
        labelmapActor.getProperty().setRGBTransferFunction(0, cfun);
        labelmapActor.getProperty().setScalarOpacity(0, ofun);
        labelmapActor.getProperty().setInterpolationTypeToNearest();
    }
    if (renderOutline) {
        labelmapActor.getProperty().setUseLabelOutline(renderOutline);
        labelmapActor.getProperty().setLabelOutlineOpacity(outlineOpacity);
        const activeSegmentIndex = getActiveSegmentIndex(segmentationRepresentation.segmentationId);
        const outlineWidths = new Array(numColors - 1);
        for (let i = 1; i < numColors; i++) {
            const isHidden = segmentsHidden.has(i);
            if (isHidden) {
                outlineWidths[i - 1] = 0;
                continue;
            }
            outlineWidths[i - 1] =
                i === activeSegmentIndex
                    ? outlineWidth + activeSegmentOutlineWidthDelta
                    : outlineWidth;
        }
        labelmapActor.getProperty().setLabelOutlineThickness(outlineWidths);
    }
    else {
        labelmapActor
            .getProperty()
            .setLabelOutlineThickness(new Array(numColors - 1).fill(0));
    }
    // Sync cache→VTK copy and mark the pipeline dirty so the GPU texture is
    // re-uploaded on every segmentation render event.
    //
    // Root cause: StackViewport.createVTKImageData() allocates a NEW empty
    // TypedArray (not a reference to the cache buffer).  updateVTKImageDataWithCornerstoneImage
    // copies cache→VTK via scalarData.set(pixelData) — but only when scrolling.
    // After brush/inference modifies the cache, VTK's copy is stale.
    // Calling scalars.modified() alone is wrong: it marks the stale copy as
    // "changed" but re-uploads the same stale data.  We must copy first.
    const inputData = labelmapActor.getMapper()?.getInputData?.();
    if (inputData) {
        const imageId = labelmapActorEntry.referencedId;
        const csImage = imageId ? cache.getImage(imageId) : null;
        if (csImage) {
            const pixelData = csImage.voxelManager?.getScalarData?.();
            const vtkScalars = inputData.getPointData?.()?.getScalars?.();
            if (pixelData && vtkScalars) {
                const vtkData = vtkScalars.getData?.();
                if (vtkData && vtkData.length === pixelData.length) {
                    vtkData.set(pixelData);
                }
                vtkScalars.modified();
            }
        }
        inputData.modified();
    }
    labelmapActor.modified();
    labelmapActor.getProperty().modified();
    labelmapActor.getMapper().modified();
    const visible = isActiveLabelmap || renderInactiveSegmentations;
    labelmapActor.setVisibility(visible);
}
function _getLabelmapConfig(labelmapConfig, isActiveLabelmap, segmentsLabelmapConfig) {
    const segmentLabelmapConfig = segmentsLabelmapConfig || {};
    const configToUse = {
        ...labelmapConfig,
        ...segmentLabelmapConfig,
    };
    const fillAlpha = isActiveLabelmap
        ? configToUse.fillAlpha
        : configToUse.fillAlphaInactive;
    const outlineWidth = isActiveLabelmap
        ? configToUse.outlineWidth
        : configToUse.outlineWidthInactive;
    const renderFill = isActiveLabelmap
        ? configToUse.renderFill
        : configToUse.renderFillInactive;
    const renderOutline = isActiveLabelmap
        ? configToUse.renderOutline
        : configToUse.renderOutlineInactive;
    const outlineOpacity = isActiveLabelmap
        ? configToUse.outlineOpacity
        : configToUse.outlineOpacityInactive;
    const activeSegmentOutlineWidthDelta = configToUse.activeSegmentOutlineWidthDelta;
    return {
        fillAlpha,
        outlineWidth,
        renderFill,
        renderOutline,
        outlineOpacity,
        activeSegmentOutlineWidthDelta,
    };
}
function _needsTransferFunctionUpdate(viewportId, segmentationId, segmentIndex, { fillAlpha, renderFill, renderOutline, segmentColor, outlineWidth, segmentsHidden, cfun, ofun, }) {
    const cacheUID = `${viewportId}-${segmentationId}-${segmentIndex}`;
    const oldConfig = labelMapConfigCache.get(cacheUID);
    if (!oldConfig) {
        labelMapConfigCache.set(cacheUID, {
            fillAlpha,
            renderFill,
            renderOutline,
            outlineWidth,
            segmentColor: segmentColor.slice(),
            segmentsHidden: new Set(segmentsHidden),
            cfunMTime: cfun.getMTime(),
            ofunMTime: ofun.getMTime(),
        });
        return {
            forceOpacityUpdate: true,
            forceColorUpdate: true,
        };
    }
    const { fillAlpha: oldFillAlpha, renderFill: oldRenderFill, renderOutline: oldRenderOutline, outlineWidth: oldOutlineWidth, segmentColor: oldSegmentColor, segmentsHidden: oldSegmentsHidden, cfunMTime: oldCfunMTime, ofunMTime: oldOfunMTime, } = oldConfig;
    const forceColorUpdate = oldSegmentColor[0] !== segmentColor[0] ||
        oldSegmentColor[1] !== segmentColor[1] ||
        oldSegmentColor[2] !== segmentColor[2];
    const forceOpacityUpdate = oldSegmentColor[3] !== segmentColor[3] ||
        oldFillAlpha !== fillAlpha ||
        oldRenderFill !== renderFill ||
        oldRenderOutline !== renderOutline ||
        oldOutlineWidth !== outlineWidth ||
        oldSegmentsHidden !== segmentsHidden;
    if (forceOpacityUpdate || forceColorUpdate) {
        labelMapConfigCache.set(cacheUID, {
            fillAlpha,
            renderFill,
            renderOutline,
            outlineWidth,
            segmentColor: segmentColor.slice(),
            segmentsHidden: new Set(segmentsHidden),
            cfunMTime: cfun.getMTime(),
            ofunMTime: ofun.getMTime(),
        });
    }
    return {
        forceOpacityUpdate,
        forceColorUpdate,
    };
}
async function _addLabelmapToViewport(viewport, labelmapData, segmentationId, config, suppressTriggerModificationEvents = false) {
    const result = await addLabelmapToElement(viewport.element, labelmapData, segmentationId, config, suppressTriggerModificationEvents);
    return result || undefined;
}
export default {
    render,
    removeRepresentation,
};
export { render, removeRepresentation };
