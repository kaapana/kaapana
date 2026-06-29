import { eventTarget, metaData } from '@cornerstonejs/core';
import {
  Enums,
  addTool,
  ProbeTool,
  RectangleROITool,
  PlanarFreehandROITool,
} from '@cornerstonejs/tools';
import { Icons } from '@ohif/ui-next';

import ToolNninter from './icons/ToolNninter';
import ToolSam from './icons/ToolSam';
import ToolTarget from './icons/ToolTarget';
import ToolVoxTell from './icons/ToolVoxTell';
import { toolboxState } from './utils/toolboxState';

const CORNERSTONE_3D_TOOLS_SOURCE_NAME = 'Cornerstone3DTools';
const CORNERSTONE_3D_TOOLS_SOURCE_VERSION = '0.1';

class Probe2Tool extends ProbeTool {
  static toolName = 'Probe2';
}

class RectangleROI2Tool extends RectangleROITool {
  static toolName = 'RectangleROI2';
}

class PlanarFreehandROI2Tool extends PlanarFreehandROITool {
  static toolName = 'PlanarFreehandROI2';
}

class PlanarFreehandROI3Tool extends PlanarFreehandROITool {
  static toolName = 'PlanarFreehandROI3';
}

const PROMPT_TOOL_NAMES = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'];
let registered = false;

function safeAddTool(tool) {
  try {
    addTool(tool);
  } catch (error) {
    if (!String(error?.message || error).includes('already')) {
      console.warn(`Failed to register ${tool.toolName}:`, error);
    }
  }
}

function addPromptToolMappings(measurementService) {
  const source =
    measurementService.getSource(
      CORNERSTONE_3D_TOOLS_SOURCE_NAME,
      CORNERSTONE_3D_TOOLS_SOURCE_VERSION
    ) ??
    measurementService.createSource(
      CORNERSTONE_3D_TOOLS_SOURCE_NAME,
      CORNERSTONE_3D_TOOLS_SOURCE_VERSION
    );
  const mappings =
    measurementService.getSourceMappings(
      CORNERSTONE_3D_TOOLS_SOURCE_NAME,
      CORNERSTONE_3D_TOOLS_SOURCE_VERSION
    ) ?? [];

  const addAlias = (alias, baseTool) => {
    if (mappings.some(mapping => mapping.annotationType === alias)) {
      return;
    }

    const baseMapping = mappings.find(mapping => mapping.annotationType === baseTool);
    if (!baseMapping) {
      console.warn(`Cannot register ${alias}; ${baseTool} measurement mapping is not available.`);
      return;
    }

    measurementService.addMapping(
      source,
      alias,
      baseMapping.matchingCriteria,
      baseMapping.toAnnotationSchema,
      baseMapping.toMeasurementSchema
    );
  };

  addAlias('Probe2', 'Probe');
  addAlias('RectangleROI2', 'RectangleROI');
  addAlias('PlanarFreehandROI2', 'PlanarFreehandROI');
  addAlias('PlanarFreehandROI3', 'PlanarFreehandROI');
}

function registerAnnotationMetadataStamping() {
  eventTarget.addEventListener(Enums.Events.ANNOTATION_ADDED, evt => {
    const annotation = (evt as any)?.detail?.annotation;
    const metadata = annotation?.metadata;
    if (!metadata || metadata.toolLoad === true || !PROMPT_TOOL_NAMES.includes(metadata.toolName)) {
      return;
    }

    metadata.neg = !!toolboxState.getPosNeg();
    if (toolboxState.getManualCorrectionMode?.()) {
      metadata.manualCorrection = true;
    }
  });
}

function registerActiveViewportInit({ servicesManager, commandsManager }) {
  const viewportGridService = servicesManager?.services?.viewportGridService;
  if (!viewportGridService?.subscribe || !commandsManager?.run) {
    return;
  }

  viewportGridService.subscribe(
    viewportGridService.EVENTS.ACTIVE_VIEWPORT_ID_CHANGED,
    ({ viewportId }) => {
      commandsManager.run('initNninter', { viewportId });
    }
  );
}

function registerMetadataProvider() {
  metaData.addProvider((type, imageId) => {
    if (type !== 'imagePlaneModule' || !imageId) {
      return;
    }

    const image = metaData.get('generalImageModule', imageId);
    const pixelSpacing = image?.PixelSpacing || image?.pixelSpacing;
    if (!Array.isArray(pixelSpacing)) {
      return;
    }

    return {
      rowPixelSpacing: Number(pixelSpacing[0]),
      columnPixelSpacing: Number(pixelSpacing[1]),
    };
  }, 9999);
}

export default function preRegistration({ servicesManager, commandsManager }: any = {}) {
  Icons.addIcon('tool-nninter', ToolNninter);
  Icons.addIcon('tool-sam', ToolSam);
  Icons.addIcon('tool-target', ToolTarget);
  Icons.addIcon('tool-voxtell', ToolVoxTell);

  safeAddTool(Probe2Tool);
  safeAddTool(RectangleROI2Tool);
  safeAddTool(PlanarFreehandROI2Tool);
  safeAddTool(PlanarFreehandROI3Tool);

  if (registered) {
    return;
  }
  registered = true;

  const measurementService = servicesManager?.services?.measurementService;
  if (measurementService) {
    addPromptToolMappings(measurementService);
  }

  registerAnnotationMetadataStamping();
  registerActiveViewportInit({ servicesManager, commandsManager });
  registerMetadataProvider();
}
