const colours = {
  'viewport-0': 'rgb(200, 0, 0)',
  'viewport-1': 'rgb(200, 200, 0)',
  'viewport-2': 'rgb(0, 200, 0)',
};

const colorsByOrientation = {
  axial: 'rgb(200, 0, 0)',
  sagittal: 'rgb(200, 200, 0)',
  coronal: 'rgb(0, 200, 0)',
};

// Prompts are not measurements: no area/length/HU text box next to them.
const promptToolConfiguration = { getTextLines: () => [] };

// The panel's prompt tools, and the brush/eraser its manual correction arms.
const promptTools = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'].map(
  toolName => ({ toolName, configuration: promptToolConfiguration })
);
const brushTools = [
  {
    toolName: 'CircularBrush',
    parentTool: 'Brush',
    configuration: { activeStrategy: 'FILL_INSIDE_CIRCLE' },
  },
  {
    toolName: 'CircularEraser',
    parentTool: 'Brush',
    configuration: { activeStrategy: 'ERASE_INSIDE_CIRCLE' },
  },
];

function getCornerstoneTools(extensionManager) {
  return extensionManager.getModuleEntry('@ohif/extension-cornerstone.utilityModule.tools').exports;
}

// Left: window/level, middle: pan, right: zoom, wheel: scroll.
function navigationTools(toolNames, Enums) {
  return [
    { toolName: toolNames.WindowLevel, bindings: [{ mouseButton: Enums.MouseBindings.Primary }] },
    { toolName: toolNames.Pan, bindings: [{ mouseButton: Enums.MouseBindings.Auxiliary }] },
    { toolName: toolNames.Zoom, bindings: [{ mouseButton: Enums.MouseBindings.Secondary }] },
    { toolName: toolNames.StackScroll, bindings: [{ mouseButton: Enums.MouseBindings.Wheel }] },
  ];
}

// The measurement tools of the toolbar, shared by the stack and MPR groups.
function measurementTools(toolNames, commandsManager) {
  const arrowTextCallback = options => commandsManager.runCommand('arrowTextCallback', options);
  return [
    { toolName: toolNames.Length },
    {
      toolName: toolNames.ArrowAnnotate,
      configuration: {
        getTextCallback: (callback, eventDetails) => arrowTextCallback({ callback, eventDetails }),
        changeTextCallback: (data, eventDetails, callback) =>
          arrowTextCallback({ callback, data, eventDetails }),
      },
    },
    { toolName: toolNames.Bidirectional },
    { toolName: toolNames.Probe },
    { toolName: toolNames.EllipticalROI },
    { toolName: toolNames.CircleROI },
    { toolName: toolNames.RectangleROI },
    { toolName: toolNames.StackScroll },
    { toolName: toolNames.Angle },
    { toolName: toolNames.CobbAngle },
    { toolName: toolNames.PlanarFreehandROI },
    { toolName: toolNames.SplineROI },
    { toolName: toolNames.LivewireContour },
    { toolName: toolNames.WindowLevelRegion },
  ];
}

function initDefaultToolGroup(extensionManager, toolGroupService, commandsManager) {
  const { toolNames, Enums } = getCornerstoneTools(extensionManager);

  toolGroupService.createToolGroupAndAddTools('default', {
    active: navigationTools(toolNames, Enums),
    passive: [
      ...measurementTools(toolNames, commandsManager),
      { toolName: toolNames.Magnify },
      { toolName: toolNames.CalibrationLine },
      { toolName: toolNames.UltrasoundDirectional },
      ...promptTools,
      ...brushTools,
    ],
    enabled: [{ toolName: toolNames.ImageOverlayViewer }, { toolName: toolNames.ReferenceLines }],
    disabled: [{ toolName: toolNames.AdvancedMagnify }],
  });
}

function initSRToolGroup(extensionManager, toolGroupService) {
  const SRUtilityModule = extensionManager.getModuleEntry(
    '@ohif/extension-cornerstone-dicom-sr.utilityModule.tools'
  );
  if (!SRUtilityModule) {
    return;
  }
  const { toolNames: SRToolNames } = SRUtilityModule.exports;
  const { toolNames, Enums } = getCornerstoneTools(extensionManager);

  toolGroupService.createToolGroupAndAddTools('SRToolGroup', {
    active: navigationTools(toolNames, Enums),
    passive: [
      { toolName: SRToolNames.SRLength },
      { toolName: SRToolNames.SRArrowAnnotate },
      { toolName: SRToolNames.SRBidirectional },
      { toolName: SRToolNames.SREllipticalROI },
      { toolName: SRToolNames.SRCircleROI },
      { toolName: SRToolNames.SRPlanarFreehandROI },
      { toolName: SRToolNames.SRRectangleROI },
      { toolName: toolNames.WindowLevelRegion },
    ],
    enabled: [{ toolName: SRToolNames.DICOMSRDisplay }],
  });
}

function initMPRToolGroup(extensionManager, toolGroupService, commandsManager) {
  const { toolNames, Enums } = getCornerstoneTools(extensionManager);
  const { cornerstoneViewportService } = extensionManager._servicesManager.services;

  toolGroupService.createToolGroupAndAddTools('mpr', {
    active: navigationTools(toolNames, Enums),
    passive: [...measurementTools(toolNames, commandsManager), ...promptTools, ...brushTools],
    disabled: [
      {
        toolName: toolNames.Crosshairs,
        configuration: {
          viewportIndicators: true,
          viewportIndicatorsConfig: {
            circleRadius: 5,
            xOffset: 0.95,
            yOffset: 0.05,
          },
          disableOnPassive: true,
          autoPan: {
            enabled: false,
            panSize: 10,
          },
          getReferenceLineColor: viewportId => {
            const viewportOptions =
              cornerstoneViewportService.getViewportInfo(viewportId)?.viewportOptions;
            if (!viewportOptions) {
              console.warn('missing viewport?', viewportId);
              return '#0c0';
            }
            return (
              colours[viewportOptions.id] ||
              colorsByOrientation[viewportOptions.orientation] ||
              '#0c0'
            );
          },
        },
      },
      { toolName: toolNames.AdvancedMagnify },
      { toolName: toolNames.ReferenceLines },
    ],
  });
}

function initVolume3DToolGroup(extensionManager, toolGroupService) {
  const { toolNames, Enums } = getCornerstoneTools(extensionManager);

  toolGroupService.createToolGroupAndAddTools('volume3d', {
    active: [
      {
        toolName: toolNames.TrackballRotateTool,
        bindings: [{ mouseButton: Enums.MouseBindings.Primary }],
      },
      { toolName: toolNames.Zoom, bindings: [{ mouseButton: Enums.MouseBindings.Secondary }] },
      { toolName: toolNames.Pan, bindings: [{ mouseButton: Enums.MouseBindings.Auxiliary }] },
    ],
  });
}

function initToolGroups(extensionManager, toolGroupService, commandsManager) {
  initDefaultToolGroup(extensionManager, toolGroupService, commandsManager);
  initSRToolGroup(extensionManager, toolGroupService);
  initMPRToolGroup(extensionManager, toolGroupService, commandsManager);
  initVolume3DToolGroup(extensionManager, toolGroupService);
}

export default initToolGroups;
