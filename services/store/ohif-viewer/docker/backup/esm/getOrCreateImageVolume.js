import { cache, volumeLoader, utilities as csUtils, } from '@cornerstonejs/core';
function getOrCreateImageVolume(referencedImageIds) {
    if (!referencedImageIds || referencedImageIds.length <= 1) {
        return;
    }
    const isValidVolume = csUtils.isValidVolume(referencedImageIds);
    if (!isValidVolume) {
        return;
    }
    const volumeId = cache.generateVolumeId(referencedImageIds);
    let imageVolume = cache.getVolume(volumeId);
    if(imageVolume && imageVolume?.voxelManager?.getCompleteScalarDataArray()?.length>0){
        return imageVolume;
    }
    imageVolume = volumeLoader.createAndCacheVolumeFromImagesSync(volumeId, referencedImageIds);
    //if (!imageVolume.voxelManager.scalarData) {
    //const voxelManager = csUtils.VoxelManager.createImageVolumeVoxelManager({
    //    imageIds: referencedImageIds,
    //    dimensions: imageVolume.dimensions,
    //    numberOfComponents: 1,
    //    id: volumeId,
    //  });
    //imageVolume.voxelManager = voxelManager;
    //}
    
    return imageVolume;
}
export default getOrCreateImageVolume;
