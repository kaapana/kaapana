// promptDisplay: owns the visual state of prompt annotations (color, lock, visibility,
// removal). Derived purely from prompt lifecycle — it holds no truth of its own.
//
// Napari reference colors: pending prompts are bright, committed (server-consumed)
// prompts are a darker shade of the same hue; positive green, negative red.

import { annotation as cornerstoneAnnotation } from '@cornerstonejs/tools';

import { applyPromptAnnotationStyle, lockPromptAnnotation } from '../utils/promptAnnotationStyle';

export function applyPending(annotationUID: string, neg: boolean): void {
  applyPromptAnnotationStyle(annotationUID, neg, { committed: false });
}

/** A submitted prompt is immutable: committed color + locked so it can never be dragged. */
export function commit(annotationUID: string, neg: boolean): void {
  applyPromptAnnotationStyle(annotationUID, neg, { committed: true });
  lockPromptAnnotation(annotationUID, true);
}

/** A failed prompt returns to editable pending state so the user can retry/adjust. */
export function unlock(annotationUID: string, neg: boolean): void {
  lockPromptAnnotation(annotationUID, false);
  applyPromptAnnotationStyle(annotationUID, neg, { committed: false });
}

export function setVisible(annotationUID: string, visible: boolean): void {
  try {
    if (cornerstoneAnnotation.visibility.isAnnotationVisible(annotationUID) !== visible) {
      cornerstoneAnnotation.visibility.setAnnotationVisibility(annotationUID, visible);
    }
  } catch (error) {
    console.warn('[nninteractive] failed to toggle prompt visibility:', error);
  }
}

export function remove(annotationUID: string): void {
  try {
    cornerstoneAnnotation.state.removeAnnotation(annotationUID);
  } catch (error) {
    console.warn('[nninteractive] failed to remove prompt annotation:', error);
  }
}
