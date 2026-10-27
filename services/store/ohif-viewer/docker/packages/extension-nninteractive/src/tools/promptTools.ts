import { PlanarFreehandROITool, ProbeTool, RectangleROITool } from '@cornerstonejs/tools';

// Prompts are drawn with renamed copies of the stock tools, so they never mix with the
// measurements of the same shape. Scribble and lasso are both freehand: an open stroke or a
// closed contour (see PROMPT_TOOL_KIND).

export class Probe2Tool extends ProbeTool {
  static toolName = 'Probe2';
}

export class RectangleROI2Tool extends RectangleROITool {
  static toolName = 'RectangleROI2';
}

export class PlanarFreehandROI2Tool extends PlanarFreehandROITool {
  static toolName = 'PlanarFreehandROI2';
}

export class PlanarFreehandROI3Tool extends PlanarFreehandROITool {
  static toolName = 'PlanarFreehandROI3';
}
