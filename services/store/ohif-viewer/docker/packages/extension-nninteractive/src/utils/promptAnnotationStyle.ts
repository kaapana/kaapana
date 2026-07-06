import { annotation as cornerstoneAnnotation } from '@cornerstonejs/tools';

// Napari reference colors (layers/abstract_layer.py): a PENDING prompt is bright, a COMMITTED
// (server-consumed) prompt is a darker shade of the same hue. Positive green, negative red.
export const PROMPT_COLOR_POS = 'rgb(0, 177, 12)';
export const PROMPT_COLOR_NEG = 'rgb(211, 7, 0)';
export const PROMPT_COLOR_POS_COMMITTED = 'rgb(0, 109, 7)';
export const PROMPT_COLOR_NEG_COMMITTED = 'rgb(143, 5, 0)';

// Pin every style variant so the pos/neg color survives hover, selection and locking.
export function applyPromptAnnotationStyle(
  annotationUID: string,
  neg: boolean,
  opts: { committed?: boolean } = {}
) {
  if (!annotationUID) {
    return;
  }
  const color = opts.committed
    ? neg
      ? PROMPT_COLOR_NEG_COMMITTED
      : PROMPT_COLOR_POS_COMMITTED
    : neg
      ? PROMPT_COLOR_NEG
      : PROMPT_COLOR_POS;
  try {
    cornerstoneAnnotation.config.style.setAnnotationStyles(annotationUID, {
      color,
      colorHighlighted: color,
      colorSelected: color,
      colorLocked: color,
    });
  } catch (error) {
    console.warn('Failed to style prompt annotation:', error);
  }
}

export function lockPromptAnnotation(annotationUID: string, locked = true) {
  if (!annotationUID) {
    return;
  }
  try {
    cornerstoneAnnotation.locking.setAnnotationLocked(annotationUID, locked);
  } catch (error) {
    console.warn('Failed to set prompt annotation lock:', error);
  }
}
