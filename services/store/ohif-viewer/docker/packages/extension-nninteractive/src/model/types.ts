// Shared types and constants for the nnInteractive model layer.
//
// The design follows docs/nninteractive-ohif-ideal-architecture.md:
// one OHIF segmentation per source series, one segment per nnInteractive object,
// prompts as locked Cornerstone annotations plus a small PromptState ledger, and a
// thin serverApi facade over the Kaapana proxy.

export type SessionStatus =
  | 'idle'
  | 'initializing'
  | 'ready'
  | 'closing'
  | 'expired'
  | 'error';

export type ViewportKind = 'stack' | 'volumeMpr' | 'volume3d' | 'unsupported';

export type PromptKind = 'point' | 'box' | 'lasso' | 'scribble';
export type PromptSign = 'positive' | 'negative';

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

/** The prompt payload the proxy accepts. Each entry is in viewer order [x, y, slice]. */
export interface PromptArrays {
  pos_points: number[][];
  neg_points: number[][];
  pos_boxes: number[][][];
  neg_boxes: number[][][];
  pos_lassos: number[][][];
  neg_lassos: number[][][];
  pos_scribbles: number[][][];
  neg_scribbles: number[][][];
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

/** Stable identity of an nnInteractive object: `${segmentationId}#${segmentIndex}`. */
export function objectKeyOf(segmentationId: string, segmentIndex: number): string {
  return `${segmentationId}#${segmentIndex}`;
}

/** Custom prompt tool names (Cornerstone aliases of the stock probe/rectangle/freehand tools). */
export const PROMPT_TOOL_NAMES = [
  'Probe2',
  'RectangleROI2',
  'PlanarFreehandROI2',
  'PlanarFreehandROI3',
] as const;

export const PROMPT_TOOL_KIND: Record<string, PromptKind> = {
  Probe2: 'point',
  RectangleROI2: 'box',
  PlanarFreehandROI2: 'scribble',
  PlanarFreehandROI3: 'lasso',
};

/** Base path for the Kaapana nnInteractive proxy (Traefik strips the prefix). */
export const NN_BASE_URL = '/nninteractive';

/** sessionStorage key for the per-browser-tab client session id. */
export const NN_CLIENT_SESSION_KEY = 'kaapana.nninteractive.clientSessionId';
