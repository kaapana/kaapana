import { eventTarget, metaData, VolumeViewport3D } from '@cornerstonejs/core';
import { Enums, addTool } from '@cornerstonejs/tools';
import { Icons } from '@ohif/ui-next';

import {
  ToolNnInteractiveBbox,
  ToolNnInteractiveLasso,
  ToolNnInteractivePoint,
  ToolNnInteractiveScribble,
} from './icons/PromptIcons';
import ToolNninter from './icons/ToolNninter';
import ToolTarget from './icons/ToolTarget';
import {
  Probe2Tool,
  RectangleROI2Tool,
  PlanarFreehandROI2Tool,
  PlanarFreehandROI3Tool,
} from './tools/promptTools';
import * as objectModel from './model/objectModel';
import * as promptModel from './model/promptModel';
import * as bridge from './model/segmentationBridge';
import { installDebugHook } from './model/debugTools';
import { objectKeyOf, PROMPT_TOOL_NAMES } from './model/types';
import { toolboxState } from './utils/toolboxState';

const PROMPT_NAMES = PROMPT_TOOL_NAMES as readonly string[];

let annotationListenersRegistered = false;
let metadataProviderRegistered = false;
let focusGuardRegistered = false;

function safeAddTool(tool: any) {
  try {
    addTool(tool);
  } catch (error) {
    if (!String((error as any)?.message || error).includes('already')) {
      console.warn(`Failed to register ${tool.toolName}:`, error);
    }
  }
}

/**
 * Prompt annotations ARE the runtime prompt display (never OHIF measurements). Stamp the
 * sign on draw and give pending style; on completion mark complete and — in live mode —
 * submit immediately. ANNOTATION_ADDED fires at draw START where box/freehand geometry is
 * a mid-drag transient, so we submit only on ANNOTATION_COMPLETED (final geometry).
 */
function registerAnnotationListeners(commandsManager: any, servicesManager: any) {
  if (annotationListenersRegistered) {
    return;
  }
  annotationListenersRegistered = true;

  eventTarget.addEventListener(Enums.Events.ANNOTATION_ADDED, (evt: any) => {
    const annotation = evt?.detail?.annotation;
    const metadata = annotation?.metadata;
    if (!metadata || metadata.toolLoad === true || !PROMPT_NAMES.includes(metadata.toolName)) {
      return;
    }
    const active = objectModel.getActiveObject(servicesManager);
    const objectKey =
      active && bridge.isManaged(active.segmentationId)
        ? objectKeyOf(active.segmentationId, active.segmentIndex)
        : undefined;
    promptModel.stampNew(annotation, { neg: !!toolboxState.getPosNeg(), objectKey });
  });

  eventTarget.addEventListener(Enums.Events.ANNOTATION_COMPLETED, (evt: any) => {
    const annotation = evt?.detail?.annotation;
    const metadata = annotation?.metadata;
    if (!metadata || !PROMPT_NAMES.includes(metadata.toolName)) {
      return;
    }
    metadata.promptCompleted = true;
    if (toolboxState.getLiveMode() && !toolboxState.getLocked() && !metadata.submitted) {
      commandsManager.run('nninter');
    }
  });
}

/** Provide row/column pixel spacing so annotation stats work when only PixelSpacing is present. */
function registerMetadataProvider() {
  if (metadataProviderRegistered) {
    return;
  }
  metadataProviderRegistered = true;

  metaData.addProvider((type: string, imageId: string) => {
    if (type !== 'imagePlaneModule' || !imageId) {
      return;
    }
    const image: any = metaData.get('generalImageModule', imageId);
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

/**
 * 3D focus state machine: a 3D viewport is never promptable. When focus returns from a 3D
 * pane to a 2D pane with a prompt tool armed, the first mousedown only focuses the viewport
 * (it is swallowed) so it does not place a prompt.
 */
function registerFocusGuard(servicesManager: any) {
  if (focusGuardRegistered || typeof document === 'undefined') {
    return;
  }
  focusGuardRegistered = true;

  const { viewportGridService, cornerstoneViewportService } = servicesManager.services;
  let wasVolume3D = false;
  let swallowNext = false;

  viewportGridService?.subscribe?.(
    viewportGridService.EVENTS.ACTIVE_VIEWPORT_ID_CHANGED,
    ({ viewportId }: any) => {
      const vp = cornerstoneViewportService.getCornerstoneViewport(viewportId);
      const is3D = vp instanceof VolumeViewport3D;
      if (wasVolume3D && !is3D) {
        swallowNext = true;
      }
      wasVolume3D = is3D;
    }
  );

  document.addEventListener(
    'mousedown',
    (event: MouseEvent) => {
      if (!swallowNext) {
        return;
      }
      swallowNext = false;
      const tool = toolboxState.getTool();
      if (tool && tool !== 'none') {
        event.stopPropagation();
        (event as any).stopImmediatePropagation?.();
      }
    },
    true
  );
}

export default function preRegistration({ servicesManager, commandsManager }: any = {}) {
  Icons.addIcon('tool-nninter', ToolNninter);
  Icons.addIcon('tool-nninteractive-point', ToolNnInteractivePoint);
  Icons.addIcon('tool-nninteractive-bbox', ToolNnInteractiveBbox);
  Icons.addIcon('tool-nninteractive-scribble', ToolNnInteractiveScribble);
  Icons.addIcon('tool-nninteractive-lasso', ToolNnInteractiveLasso);
  Icons.addIcon('tool-target', ToolTarget);

  safeAddTool(Probe2Tool);
  safeAddTool(RectangleROI2Tool);
  safeAddTool(PlanarFreehandROI2Tool);
  safeAddTool(PlanarFreehandROI3Tool);

  if (servicesManager && commandsManager) {
    installDebugHook(servicesManager);
    registerAnnotationListeners(commandsManager, servicesManager);
    registerFocusGuard(servicesManager);
  }
  registerMetadataProvider();
}
