import { eventTarget, VolumeViewport3D } from '@cornerstonejs/core';
import { Enums, addTool } from '@cornerstonejs/tools';
import { Icons } from '@ohif/ui-next';

import ToolNninter from './icons/ToolNninter';
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
import { isPromptTool } from './model/types';
import { toolboxState } from './utils/toolboxState';

let annotationListenersRegistered = false;
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
    const annotation = evt.detail.annotation;
    if (!toolboxState.get().modeActive || !isPromptTool(annotation?.metadata?.toolName)) {
      return;
    }
    const active = objectModel.getActiveObject(servicesManager);
    const owner = active && bridge.isManaged(active.segmentationId) ? active : null;
    promptModel.stampNew(annotation, toolboxState.get().negative, owner);
  });

  eventTarget.addEventListener(Enums.Events.ANNOTATION_COMPLETED, (evt: any) => {
    const metadata = evt.detail.annotation?.metadata;
    if (!toolboxState.get().modeActive || !isPromptTool(metadata?.toolName)) {
      return;
    }
    metadata.promptCompleted = true;
    if (toolboxState.get().liveMode && !metadata.submitted) {
      commandsManager.run('nninter');
    }
  });
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
      if (!toolboxState.get().modeActive) {
        return;
      }
      const targetId = transitionTargetId(event);
      if (!targetId) {
        return;
      }
      if (toolboxState.get().tool === 'none') {
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

  safeAddTool(Probe2Tool);
  safeAddTool(RectangleROI2Tool);
  safeAddTool(PlanarFreehandROI2Tool);
  safeAddTool(PlanarFreehandROI3Tool);

  if (servicesManager && commandsManager) {
    installDebugHook(servicesManager);
    registerAnnotationListeners(commandsManager, servicesManager);
    registerFocusGuard(servicesManager);
  }
}
