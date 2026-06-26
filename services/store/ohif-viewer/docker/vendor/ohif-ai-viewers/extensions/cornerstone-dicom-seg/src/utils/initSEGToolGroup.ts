import initCornerstoneTools from '../../../cornerstone/src/initCornerstoneTools';

function createSEGToolGroupAndAddTools(ToolGroupService, customizationService, toolGroupId) {
  //const { tools } = customizationService.get('cornerstone.overlayViewportTools') ?? {};

  return initCornerstoneTools()//ToolGroupService.createToolGroupAndAddTools(toolGroupId, tools);
}

export default createSEGToolGroupAndAddTools;
