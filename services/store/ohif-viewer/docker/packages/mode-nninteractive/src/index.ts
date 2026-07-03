import i18n from 'i18next';
import { id } from './id';
import initToolGroups from './initToolGroups';
import toolbarButtons from './toolbarButtons';

const NON_IMAGE_MODALITIES = ['ECG', 'SEG', 'RTSTRUCT', 'RTPLAN', 'PR'];

const ohif = {
  layout: '@ohif/extension-default.layoutTemplateModule.viewerLayout',
  sopClassHandler: '@ohif/extension-default.sopClassHandlerModule.stack',
  wsiSopClassHandler:
    '@ohif/extension-cornerstone.sopClassHandlerModule.DicomMicroscopySopClassHandler',
};

const cornerstone = {
  segmentation: '@kaapana/extension-nninteractive.panelModule.panelSegmentationWithTools',
};

const tracked = {
  thumbnailList: '@ohif/extension-measurement-tracking.panelModule.seriesList',
  viewport: '@ohif/extension-measurement-tracking.viewportModule.cornerstone-tracked',
};

const dicomsr = {
  sopClassHandler: '@ohif/extension-cornerstone-dicom-sr.sopClassHandlerModule.dicom-sr',
  sopClassHandler3D: '@ohif/extension-cornerstone-dicom-sr.sopClassHandlerModule.dicom-sr-3d',
  viewport: '@ohif/extension-cornerstone-dicom-sr.viewportModule.dicom-sr',
};

const dicomvideo = {
  sopClassHandler: '@ohif/extension-dicom-video.sopClassHandlerModule.dicom-video',
  viewport: '@ohif/extension-dicom-video.viewportModule.dicom-video',
};

const dicompdf = {
  sopClassHandler: '@ohif/extension-dicom-pdf.sopClassHandlerModule.dicom-pdf',
  viewport: '@ohif/extension-dicom-pdf.viewportModule.dicom-pdf',
};

const dicomSeg = {
  sopClassHandler: '@ohif/extension-cornerstone-dicom-seg.sopClassHandlerModule.dicom-seg',
  viewport: '@ohif/extension-cornerstone-dicom-seg.viewportModule.dicom-seg',
};

const dicomPmap = {
  sopClassHandler: '@ohif/extension-cornerstone-dicom-pmap.sopClassHandlerModule.dicom-pmap',
  viewport: '@ohif/extension-cornerstone-dicom-pmap.viewportModule.dicom-pmap',
};

const dicomRT = {
  viewport: '@ohif/extension-cornerstone-dicom-rt.viewportModule.dicom-rt',
  sopClassHandler: '@ohif/extension-cornerstone-dicom-rt.sopClassHandlerModule.dicom-rt',
};

const extensionDependencies = {
  '@ohif/extension-default': '^3.0.0',
  '@ohif/extension-cornerstone': '^3.0.0',
  '@ohif/extension-measurement-tracking': '^3.0.0',
  '@ohif/extension-cornerstone-dicom-sr': '^3.0.0',
  '@ohif/extension-cornerstone-dicom-seg': '^3.0.0',
  '@ohif/extension-cornerstone-dicom-pmap': '^3.0.0',
  '@ohif/extension-cornerstone-dicom-rt': '^3.0.0',
  '@ohif/extension-dicom-pdf': '^3.0.1',
  '@ohif/extension-dicom-video': '^3.0.1',
  '@kaapana/extension-nninteractive': '^3.10.4',
};

const HOTKEY_PREFERENCES_VERSION = 'nninteractive-move40-v1';

function resetStaleHotkeyPreferences() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }

  const versionKey = 'kaapana-nninteractive-hotkeys-version';
  if (window.localStorage.getItem(versionKey) === HOTKEY_PREFERENCES_VERSION) {
    return;
  }

  window.localStorage.removeItem('user-preferred-keys');
  window.localStorage.removeItem('hotkey-definitions');
  window.localStorage.setItem('hotkeys-migrated', 'true');
  window.localStorage.setItem(versionKey, HOTKEY_PREFERENCES_VERSION);
}

function migrateHotkeyBindings(bindings = []) {
  return bindings
    .filter(binding => {
      if (binding.commandName === 'addNewSegment') {
        return false;
      }

      return !(
        binding.commandName === 'setToolActive' &&
        binding.commandOptions?.toolName === 'CircularBrush'
      );
    })
    .map(binding => {
      switch (binding.commandName) {
        case 'rotateViewportCW':
          return { ...binding, keys: ['ctrl+r'] };
        case 'rotateViewportCCW':
          return { ...binding, keys: ['ctrl+l'] };
        case 'flipViewportVertical':
          return { ...binding, keys: ['ctrl+v'] };
        case 'undo':
          return { ...binding, keys: ['ctrl+shift+z'] };
        default:
          return binding;
      }
    })
    .concat([
      {
        commandName: 'toggleSegmentationVisibilityAllViewports',
        label: 'Toggle Segmentation Visibility (All Viewports)',
        keys: ['v'],
        isEditable: true,
      },
      {
        commandName: 'undoNninter',
        label: 'Undo NNInteractive',
        keys: ['ctrl+z'],
        isEditable: true,
      },
      {
        commandName: 'resetNninter',
        label: 'Reset NNInteractive',
        keys: ['g'],
        isEditable: true,
      },
      {
        commandName: 'setToolActive',
        commandOptions: { toolName: 'CircularBrush' },
        label: 'Brush',
        keys: ['ctrl+b'],
        isEditable: true,
      },
    ]);
}

function installHotkeyRegistrationGuard(extensionManager) {
  const hotkeysManager = extensionManager?._hotkeysManager;
  if (!hotkeysManager || hotkeysManager.__nnInteractiveHotkeyGuardInstalled) {
    return;
  }

  const registerHotkeys = hotkeysManager.registerHotkeys.bind(hotkeysManager);
  hotkeysManager.registerHotkeys = definition => {
    try {
      registerHotkeys(definition);
    } catch (error) {
      console.error('Failed to register nnInteractive hotkey definition:', definition, error);
    }
  };
  hotkeysManager.__nnInteractiveHotkeyGuardInstalled = true;
}

function modeFactory({ modeConfiguration }) {
  let _activatePanelTriggersSubscriptions = [];

  return {
    id,
    routeName: 'viewer',
    displayName: i18n.t('Modes:Basic Viewer'),
    onModeEnter: function ({ servicesManager, extensionManager, commandsManager }: withAppTypes) {
      const { measurementService, toolbarService, toolGroupService, customizationService } =
        servicesManager.services;

      measurementService.clearMeasurements();

      resetStaleHotkeyPreferences();
      installHotkeyRegistrationGuard(extensionManager);

      initToolGroups(extensionManager, toolGroupService, commandsManager);
      toolbarService.addButtons(toolbarButtons);
      toolbarService.createButtonSection('primary', [
        'MeasurementTools',
        'Zoom',
        'Pan',
        'TrackballRotate',
        'WindowLevel',
        'Capture',
        'Layout',
        'Crosshairs',
        'MoreTools',
      ]);

      toolbarService.createButtonSection('measurementSection', [
        'Length',
        'Bidirectional',
        'ArrowAnnotate',
        'EllipticalROI',
        'RectangleROI',
        'CircleROI',
        'PlanarFreehandROI',
        'SplineROI',
        'LivewireContour',
      ]);

      toolbarService.createButtonSection('moreToolsSection', [
        'Reset',
        'rotate-right',
        'flipHorizontal',
        'ImageSliceSync',
        'ReferenceLines',
        'ImageOverlayViewer',
        'StackScroll',
        'invert',
        'Probe',
        'Cine',
        'Angle',
        'CobbAngle',
        'Magnify',
        'CalibrationLine',
        'TagBrowser',
        'AdvancedMagnify',
        'UltrasoundDirectionalTool',
        'WindowLevelRegion',
      ]);

      customizationService.setCustomizations({
        'panelSegmentation.disableEditing': {
          $set: false,
        },
        'ohif.hotkeyBindings': {
          $apply: migrateHotkeyBindings,
        },
      });

      toolbarService.createButtonSection('segmentationToolbox', [
        'SegmentationUtilities',
        'SegmentationTools',
      ]);

      toolbarService.createButtonSection('aiToolBox', ['aiToolBoxContainer']);

      toolbarService.createButtonSection('aiToolBoxSection', [
        'Probe2',
        'PlanarFreehandROI2',
        'PlanarFreehandROI3',
        'RectangleROI2',
        'nninter',
        'undoNninter',
      ]);
      toolbarService.createButtonSection('segmentationToolboxUtilitySection', [
        'InterpolateLabelmap',
        'SegmentBidirectional',
      ]);
      toolbarService.createButtonSection('segmentationToolboxToolsSection', [
        'BrushTools',
        'Shapes',
      ]);
      toolbarService.createButtonSection('brushToolsSection', ['Brush', 'Eraser', 'Threshold']);
    },
    onModeExit: ({ servicesManager }: withAppTypes) => {
      const {
        toolGroupService,
        syncGroupService,
        segmentationService,
        cornerstoneViewportService,
        uiDialogService,
        uiModalService,
      } = servicesManager.services;

      _activatePanelTriggersSubscriptions.forEach(sub => sub.unsubscribe());
      _activatePanelTriggersSubscriptions = [];

      uiDialogService.hideAll();
      uiModalService.hide();
      toolGroupService.destroy();
      syncGroupService.destroy();
      segmentationService.destroy();
      cornerstoneViewportService.destroy();
    },
    validationTags: {
      study: [],
      series: [],
    },
    isValidMode: function ({ modalities }) {
      const modalitiesList = modalities.split('\\');

      return {
        valid: !!modalitiesList.filter(modality => NON_IMAGE_MODALITIES.indexOf(modality) === -1)
          .length,
        description:
          'The mode does not support studies that ONLY include the following modalities: SM, ECG, SEG, RTSTRUCT',
      };
    },
    routes: [
      {
        path: 'longitudinal',
        layoutTemplate: () => {
          return {
            id: ohif.layout,
            props: {
              leftPanels: [tracked.thumbnailList],
              leftPanelResizable: true,
              rightPanels: [cornerstone.segmentation],
              rightPanelClosed: false,
              rightPanelResizable: true,
              viewports: [
                {
                  namespace: tracked.viewport,
                  displaySetsToDisplay: [
                    ohif.sopClassHandler,
                    dicomvideo.sopClassHandler,
                    dicomsr.sopClassHandler3D,
                    ohif.wsiSopClassHandler,
                  ],
                },
                {
                  namespace: dicomsr.viewport,
                  displaySetsToDisplay: [dicomsr.sopClassHandler],
                },
                {
                  namespace: dicompdf.viewport,
                  displaySetsToDisplay: [dicompdf.sopClassHandler],
                },
                {
                  namespace: dicomSeg.viewport,
                  displaySetsToDisplay: [dicomSeg.sopClassHandler],
                },
                {
                  namespace: dicomPmap.viewport,
                  displaySetsToDisplay: [dicomPmap.sopClassHandler],
                },
                {
                  namespace: dicomRT.viewport,
                  displaySetsToDisplay: [dicomRT.sopClassHandler],
                },
              ],
            },
          };
        },
      },
    ],
    extensions: extensionDependencies,
    hangingProtocol: 'default',
    sopClassHandlers: [
      dicomvideo.sopClassHandler,
      dicomSeg.sopClassHandler,
      dicomPmap.sopClassHandler,
      ohif.sopClassHandler,
      ohif.wsiSopClassHandler,
      dicompdf.sopClassHandler,
      dicomsr.sopClassHandler3D,
      dicomsr.sopClassHandler,
      dicomRT.sopClassHandler,
    ],
    ...modeConfiguration,
  };
}

const mode = {
  id,
  modeFactory,
  extensionDependencies,
};

export default mode;
