import { getEnabledElement, addVolumesToViewports, addImageSlicesToViewports, Enums, cache, BaseVolumeViewport, volumeLoader, utilities, } from '@cornerstonejs/core';
import { getCurrentLabelmapImageIdsForViewport } from '../../../stateManagement/segmentation/getCurrentLabelmapImageIdForViewport';
import { getSegmentation } from '../../../stateManagement/segmentation/getSegmentation';
import { triggerSegmentationDataModified, triggerSegmentationModified, } from '../../../stateManagement/segmentation/triggerSegmentationEvents';
import { SegmentationRepresentations } from '../../../enums';
import { addVolumesAsIndependentComponents } from './addVolumesAsIndependentComponents';
const { uuidv4 } = utilities;
async function addLabelmapToElement(element, labelMapData, segmentationId, config, suppressTriggerModificationEvents = false) {
    const enabledElement = getEnabledElement(element);
    const { renderingEngine, viewport } = enabledElement;
    const { id: viewportId } = viewport;
    const visibility = true;
    const immediateRender = false;
    const suppressEvents = true;
    if (viewport instanceof BaseVolumeViewport) {
        const volumeLabelMapData = labelMapData;
        const volumeId = _ensureVolumeHasVolumeId(volumeLabelMapData, segmentationId);
        if (!cache.getVolume(volumeId)) {
            await _handleMissingVolume(labelMapData);
        }
        let blendMode = config?.blendMode ?? Enums.BlendModes.MAXIMUM_INTENSITY_BLEND;
        let useIndependentComponents = blendMode === Enums.BlendModes.LABELMAP_EDGE_PROJECTION_BLEND;
        if (useIndependentComponents) {
            const referenceVolumeId = viewport.getVolumeId();
            const baseVolume = cache.getVolume(referenceVolumeId);
            const segVolume = cache.getVolume(volumeId);
            const segDims = segVolume.dimensions;
            const refDims = baseVolume.dimensions;
            if (segDims[0] !== refDims[0] ||
                segDims[1] !== refDims[1] ||
                segDims[2] !== refDims[2]) {
                useIndependentComponents = false;
                blendMode = Enums.BlendModes.MAXIMUM_INTENSITY_BLEND;
                console.debug('Dimensions mismatch - falling back to regular volume addition');
            }
        }
        const volumeInputs = [
            {
                volumeId,
                visibility,
                representationUID: `${segmentationId}-${SegmentationRepresentations.Labelmap}`,
                useIndependentComponents,
                blendMode,
            },
        ];
        if (!volumeInputs[0].useIndependentComponents) {
            await addVolumesToViewports(renderingEngine, volumeInputs, [viewportId], immediateRender, suppressEvents);
        }
        else {
            const result = await addVolumesAsIndependentComponents({
                viewport,
                volumeInputs,
                segmentationId,
            });
            return result;
        }
    }
    else {
        const segmentationImageIds = getCurrentLabelmapImageIdsForViewport(viewport.id, segmentationId);
        const stackInputs = segmentationImageIds.map((imageId) => {
            //Specifiy actorUID to be the same as the representationUID
            const representationUID = `${segmentationId}-${SegmentationRepresentations.Labelmap}-${imageId}`;
            return {
                imageId,
                representationUID,
                actorUID: representationUID,
            };
        });
        addImageSlicesToViewports(renderingEngine, stackInputs, [viewportId]);
    }
    if (!suppressTriggerModificationEvents) {
        triggerSegmentationDataModified(segmentationId);
    }
}
function _ensureVolumeHasVolumeId(labelMapData, segmentationId) {
    let { volumeId } = labelMapData;
    if (!volumeId) {
        volumeId = uuidv4();
        const segmentation = getSegmentation(segmentationId);
        segmentation.representationData.Labelmap = {
            ...segmentation.representationData.Labelmap,
            volumeId,
        };
        labelMapData.volumeId = volumeId;
        triggerSegmentationModified(segmentationId);
    }
    return volumeId;
}
async function _handleMissingVolume(labelMapData) {
    const stackData = labelMapData;
    const hasImageIds = stackData.imageIds.length > 0;
    if (!hasImageIds) {
        throw new Error('cannot create labelmap, no imageIds found for the volume labelmap');
    }
    const volume = await volumeLoader.createAndCacheVolumeFromImages(labelMapData.volumeId || uuidv4(), stackData.imageIds);
    return volume;
}
export default addLabelmapToElement;
