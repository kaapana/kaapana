import { eventTarget, metaData } from '@cornerstonejs/core';
import {
  Enums,
  addTool,
  annotation as cornerstoneAnnotation,
} from '@cornerstonejs/tools';
import { Icons } from '@ohif/ui-next';

import ToolNninter from './icons/ToolNninter';
import ToolTarget from './icons/ToolTarget';
import {
  Probe2Tool,
  RectangleROI2Tool,
  PlanarFreehandROI2Tool,
  PlanarFreehandROI3Tool,
} from './tools/promptTools';
import { dispatchMeasurementStateChanged } from './utils/measurementStateChanged';
import { toolboxState } from './utils/toolboxState';

const CORNERSTONE_3D_TOOLS_SOURCE_NAME = 'Cornerstone3DTools';
const CORNERSTONE_3D_TOOLS_SOURCE_VERSION = '0.1';

const PROMPT_TOOL_NAMES = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'];
let annotationMetadataStampingRegistered = false;
let metadataProviderRegistered = false;
let toolLoadMeasurementVisibilityRegistered = false;

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

  const addAlias = (alias: string, baseTool: string) => {
    if (mappings.some(mapping => mapping.annotationType === alias)) {
      return;
    }

    const baseMapping = mappings.find(mapping => mapping.annotationType === baseTool);
    if (!baseMapping) {
      console.warn(`Cannot register ${alias}; ${baseTool} measurement mapping is not available.`);
      return;
    }

    const toAnnotationSchema = measurement => {
      const baseMeasurement = {
        ...measurement,
        toolName: baseTool,
        metadata: {
          ...measurement?.metadata,
          toolName: baseTool,
        },
      };
      const annotation = baseMapping.toAnnotationSchema(baseMeasurement);

      if (annotation?.metadata) {
        annotation.metadata.toolName = alias;
      }

      return annotation;
    };

    const toMeasurementSchema = sourceAnnotationDetail => {
      const annotation = sourceAnnotationDetail?.annotation;
      const baseSourceAnnotationDetail = {
        ...sourceAnnotationDetail,
        annotation: {
          ...annotation,
          metadata: {
            ...annotation?.metadata,
            toolName: baseTool,
          },
        },
      };
      const measurement = baseMapping.toMeasurementSchema(baseSourceAnnotationDetail);

      if (!measurement) {
        return measurement;
      }

      return {
        ...measurement,
        toolName: alias,
        metadata: {
          ...measurement.metadata,
          ...annotation?.metadata,
          toolName: alias,
        },
      };
    };

    measurementService.addMapping(
      source,
      alias,
      baseMapping.matchingCriteria,
      toAnnotationSchema,
      toMeasurementSchema
    );
  };

  addAlias('Probe2', 'Probe');
  addAlias('RectangleROI2', 'RectangleROI');
  addAlias('PlanarFreehandROI2', 'PlanarFreehandROI');
  addAlias('PlanarFreehandROI3', 'PlanarFreehandROI');
}

function registerAnnotationMetadataStamping() {
  if (annotationMetadataStampingRegistered) {
    return;
  }
  annotationMetadataStampingRegistered = true;

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

function registerMetadataProvider() {
  if (metadataProviderRegistered) {
    return;
  }
  metadataProviderRegistered = true;

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

function registerToolLoadMeasurementVisibility(measurementService) {
  if (toolLoadMeasurementVisibilityRegistered || !measurementService?.subscribe) {
    return;
  }
  toolLoadMeasurementVisibilityRegistered = true;

  measurementService.subscribe(measurementService.EVENTS.MEASUREMENT_ADDED, ({ measurement }) => {
    if (!measurement?.metadata?.toolLoad || measurement.isVisible === false) {
      return;
    }

    try {
      measurementService.toggleVisibilityMeasurement?.(measurement.uid, false);
    } catch (error) {
      console.warn('Failed to hide toolLoad measurement through MeasurementService:', error);
    }

    try {
      if (cornerstoneAnnotation.visibility.isAnnotationVisible(measurement.uid)) {
        cornerstoneAnnotation.visibility.setAnnotationVisibility(measurement.uid, false);
      }
    } catch (error) {
      console.warn('Failed to hide toolLoad annotation:', error);
    }

    dispatchMeasurementStateChanged();
  });
}

export default function preRegistration({ servicesManager, commandsManager }: any = {}) {
  Icons.addIcon('tool-nninter', ToolNninter);
  Icons.addIcon('tool-target', ToolTarget);

  safeAddTool(Probe2Tool);
  safeAddTool(RectangleROI2Tool);
  safeAddTool(PlanarFreehandROI2Tool);
  safeAddTool(PlanarFreehandROI3Tool);

  const measurementService = servicesManager?.services?.measurementService;
  if (measurementService) {
    addPromptToolMappings(measurementService);
    registerToolLoadMeasurementVisibility(measurementService);
  }

  registerAnnotationMetadataStamping();
  registerMetadataProvider();
}
