// Shared types and constants for the nnInteractive model layer.
//
// Each nnInteractive object is one segment of a shared OHIF "layer" segmentation (objects that
// would overlap live in different layers — see segmentationBridge), prompts are locked
// Cornerstone annotations plus a small ledger (promptModel), and serverApi is a thin facade
// over the Kaapana proxy.

export type SessionStatus = 'idle' | 'initializing' | 'ready' | 'expired' | 'error';

export type ViewportKind = 'stack' | 'volumeMpr' | 'volume3d' | 'unsupported';

export type PromptKind = 'point' | 'box' | 'lasso' | 'scribble';

/** Where an object lives: its layer segmentation and its segment index (= voxel value). */
export interface ObjectRef {
  segmentationId: string;
  segmentIndex: number;
}

/** Stable identity of an nnInteractive object: `${segmentationId}#${segmentIndex}`. */
export function objectKeyOf({ segmentationId, segmentIndex }: ObjectRef): string {
  return `${segmentationId}#${segmentIndex}`;
}

/** The source image series an nnInteractive session operates on. */
export interface SourceImage {
  studyInstanceUID: string;
  seriesInstanceUID: string;
  displaySetInstanceUID: string;
  /** Source display-set image ids in slice order (the order the proxy expects). */
  imageIds: string[];
  seriesDescription?: string;
}

/**
 * A prediction crop as returned by the proxy. Coordinates are model order [z, y, x].
 * `flipped` means the client must reverse the z axis to map back to viewer slices.
 */
export interface PredictionCrop {
  seg: Uint8Array;
  scope: 'full' | 'delta' | 'unchanged';
  offset: [number, number, number]; // [z0, y0, x0]
  fullShape: [number, number, number]; // [Z, Y, X]
  cropShape: [number, number, number]; // [dz, dy, dx]
  flipped: boolean;
  meta: Record<string, any>;
}

export interface FreehandPrompt {
  /** Voxel polyline in viewer/source order [x, y, slice]. */
  points: number[][];
  /** Constant plane axis in the same [x, y, slice] coordinate order. */
  axis?: number;
}

/** The prompt payload the proxy accepts. Each entry is in viewer order [x, y, slice]. */
export interface PromptArrays {
  pos_points: number[][];
  neg_points: number[][];
  pos_boxes: number[][][];
  neg_boxes: number[][][];
  pos_lassos: FreehandPrompt[];
  neg_lassos: FreehandPrompt[];
  pos_scribbles: FreehandPrompt[];
  neg_scribbles: FreehandPrompt[];
}

export function emptyPromptArrays(): PromptArrays {
  return {
    pos_points: [],
    neg_points: [],
    pos_boxes: [],
    neg_boxes: [],
    pos_lassos: [],
    neg_lassos: [],
    pos_scribbles: [],
    neg_scribbles: [],
  };
}

/** Prompt tools (renamed copies of the stock probe/rectangle/freehand tools) by prompt kind. */
export const PROMPT_TOOL_KIND: Readonly<Record<string, PromptKind>> = {
  Probe2: 'point',
  RectangleROI2: 'box',
  PlanarFreehandROI2: 'scribble',
  PlanarFreehandROI3: 'lasso',
};

export function isPromptTool(toolName: unknown): boolean {
  return typeof toolName === 'string' && Object.hasOwn(PROMPT_TOOL_KIND, toolName);
}
