// promptDisplay: owns the visual state of prompt annotations (color, lock, visibility,
// removal). Derived purely from prompt lifecycle — it holds no truth of its own.

import { annotation as cornerstoneAnnotation } from '@cornerstonejs/tools';

// Napari reference colors (layers/abstract_layer.py): a pending prompt is bright, a committed
// (server-consumed) prompt is a darker shade of the same hue. Positive green, negative red.
const COLORS = {
  pending: { positive: 'rgb(0, 177, 12)', negative: 'rgb(211, 7, 0)' },
  committed: { positive: 'rgb(0, 109, 7)', negative: 'rgb(143, 5, 0)' },
};

function warnOnError(action: string, fn: () => void): void {
  try {
    fn();
  } catch (error) {
    console.warn(`[nninteractive] failed to ${action} prompt annotation:`, error);
  }
}

// Pin every style variant so the pos/neg color survives hover, selection and locking.
function style(annotationUID: string, neg: boolean, state: keyof typeof COLORS): void {
  const color = COLORS[state][neg ? 'negative' : 'positive'];
  warnOnError('style', () =>
    cornerstoneAnnotation.config.style.setAnnotationStyles(annotationUID, {
      color,
      colorHighlighted: color,
      colorSelected: color,
      colorLocked: color,
    })
  );
}

function lock(annotationUID: string, locked: boolean): void {
  warnOnError('lock', () =>
    cornerstoneAnnotation.locking.setAnnotationLocked(annotationUID, locked)
  );
}

export function applyPending(annotationUID: string, neg: boolean): void {
  style(annotationUID, neg, 'pending');
}

/** A submitted prompt is immutable: committed color + locked so it can never be dragged. */
export function commit(annotationUID: string, neg: boolean): void {
  style(annotationUID, neg, 'committed');
  lock(annotationUID, true);
}

/** A failed prompt returns to editable pending state so the user can retry/adjust. */
export function unlock(annotationUID: string, neg: boolean): void {
  lock(annotationUID, false);
  style(annotationUID, neg, 'pending');
}

export function setVisible(annotationUID: string, visible: boolean): void {
  warnOnError('toggle', () => {
    if (cornerstoneAnnotation.visibility.isAnnotationVisible(annotationUID) !== visible) {
      cornerstoneAnnotation.visibility.setAnnotationVisibility(annotationUID, visible);
    }
  });
}

export function remove(annotationUID: string): void {
  warnOnError('remove', () => cornerstoneAnnotation.state.removeAnnotation(annotationUID));
}
