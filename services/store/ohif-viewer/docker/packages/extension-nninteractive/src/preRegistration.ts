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
 * 3D focus guard: a 3D viewport is never promptable. When the active pane is 3D and the user
 * clicks a 2D pane to switch to it, that click must ONLY focus the 2D pane — not immediately
 * place a prompt.
 *
 * We detect the transition at INPUT time by reading the currently-active viewport (the pane the
 * click is leaving). Reacting to ACTIVE_VIEWPORT_ID_CHANGED instead — as an earlier version did —
 * is too late: that event fires as a *result* of this same click, after the prompt tool has
 * already handled it, so the guard ended up swallowing the *next* click rather than the
 * transition one. When the active pane is 3D and the click lands on a different pane with a tool
 * armed, we swallow the whole pointer interaction (so neither pointer- nor mouse-driven tools
 * act) and move focus explicitly, so swallowing can never strand the user on the 3D pane.
 */
function registerFocusGuard(servicesManager: any) {
  if (focusGuardRegistered || typeof document === 'undefined') {
    return;
  }
  focusGuardRegistered = true;

  const { viewportGridService, cornerstoneViewportService } = servicesManager.services;

  // If the active viewport is 3D and `event` targets a DIFFERENT viewport, return that pane's id
  // (the transition target); otherwise undefined.
  const transitionTargetId = (event: Event): string | undefined => {
    const activeId = viewportGridService?.getActiveViewportId?.();
    if (!activeId) {
      return undefined;
    }
    const activeVp = cornerstoneViewportService.getCornerstoneViewport(activeId);
    if (!(activeVp instanceof VolumeViewport3D)) {
      return undefined;
    }
    const target = event.target as Node | null;
    if (!target) {
      return undefined;
    }
    for (const id of cornerstoneViewportService.getViewportIds?.() ?? []) {
      const el = cornerstoneViewportService.getCornerstoneViewport(id)?.element;
      if (el && el.contains(target)) {
        return id === activeId ? undefined : id; // inside the 3D pane itself → not a transition
      }
    }
    return undefined;
  };

  // True from the transition pointerdown until the next pointerdown, so the entire click
  // interaction (mousedown/up, pointerup, click) is suppressed for exactly that one transition.
  let swallowInteraction = false;

  document.addEventListener(
    'pointerdown',
    (event: PointerEvent) => {
      swallowInteraction = false;
      const targetId = transitionTargetId(event);
      if (!targetId) {
        return;
      }
      const tool = toolboxState.getTool();
      if (!tool || tool === 'none') {
        return; // nothing armed → the click just focuses; nothing to suppress
      }
      swallowInteraction = true;
      event.stopPropagation();
      (event as any).stopImmediatePropagation?.();
      try {
        viewportGridService.setActiveViewportId?.(targetId);
      } catch {
        // ignore — worst case the user clicks once more to focus
      }
    },
    true
  );

  for (const type of ['mousedown', 'mouseup', 'pointerup', 'click']) {
    document.addEventListener(
      type,
      (event: Event) => {
        if (!swallowInteraction) {
          return;
        }
        event.stopPropagation();
        (event as any).stopImmediatePropagation?.();
      },
      true
    );
  }
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
