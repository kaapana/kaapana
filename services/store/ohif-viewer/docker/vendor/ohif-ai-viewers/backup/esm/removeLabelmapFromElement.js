import { getEnabledElement } from '@cornerstonejs/core';
import { getLabelmapActorEntries } from '../../../stateManagement/segmentation/helpers/getSegmentationActor';
function removeLabelmapFromElement(element, segmentationId) {
    const enabledElement = getEnabledElement(element);
    const { viewport } = enabledElement;
    // Remove ALL labelmap actors for this segmentation, not just the first match.
    // A viewport can end up with more than one labelmap actor for the same
    // segmentation (e.g. a leftover volume-style actor whose uid is a UUID
    // alongside the visible stack-style actor `${segmentationId}-Labelmap-${imageId}`,
    // typically after a stack<->volume viewport conversion). The stock
    // getLabelmapActorUID returns only the first match, so removeActors would
    // delete one and leave the other orphaned on the canvas until the viewport
    // is rebuilt. Removing every matching entry guarantees a clean unload.
    const entries = getLabelmapActorEntries(viewport.id, segmentationId) || [];
    const uids = entries.map((entry) => entry.uid).filter(Boolean);
    if (uids.length > 0) {
        viewport.removeActors(uids);
    }
}
export default removeLabelmapFromElement;
