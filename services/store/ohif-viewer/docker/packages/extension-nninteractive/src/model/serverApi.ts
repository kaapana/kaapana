// serverApi: the single transport facade to the nnInteractive backend.
//
// Nothing else in the plugin knows the proxy's URLs. Callers pass source-voxel coordinates
// and receive typed prediction crops; they never build URLs, headers, or multipart bodies.
//
// Protocol (see the FastAPI proxy): POST /nninteractive/infer/segmentation?image=<seriesUID>
// with a multipart form whose `params` field is a JSON object carrying the `nninter`
// discriminator (init | true | undo | reset | set_mask), studyInstanceUID, clientSessionID
// and the prompt arrays. Responses are multipart (meta JSON + seg bytes); meta carries
// pred_scope/pred_offset/pred_full_shape/pred_crop_shape/flipped.

import axios from 'axios';
import { metaData } from '@cornerstonejs/core';

import { parseMultipart } from '../utils/multipart';
import { PredictionCrop, PromptArrays, SourceImage } from './types';

/**
 * Base path for the Kaapana nnInteractive proxy (Traefik strips the prefix). Under
 * /project/<id>/ohif the proxy is reached through the same project prefix, so auth scopes
 * its image reads to that project.
 */
const BASE_URL = `${window.location.pathname.match(/^\/project\/[^/]+/)?.[0] ?? ''}/nninteractive`;

/** sessionStorage key for the per-browser-tab client session id. */
const CLIENT_SESSION_KEY = 'kaapana.nninteractive.clientSessionId';

let clientSessionId: string | undefined;

/** One backend session per browser tab: the id survives reloads but not a new tab. */
function getClientSessionId(): string {
  if (clientSessionId) {
    return clientSessionId;
  }
  try {
    clientSessionId = window.sessionStorage.getItem(CLIENT_SESSION_KEY) ?? undefined;
  } catch {
    // sessionStorage may be unavailable; fall back to a runtime-only id.
  }
  if (!clientSessionId) {
    // randomUUID exists only in secure contexts (https, localhost).
    clientSessionId =
      globalThis.crypto?.randomUUID?.() ??
      `nn-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    try {
      window.sessionStorage.setItem(CLIENT_SESSION_KEY, clientSessionId);
    } catch {
      // ignore
    }
  }
  return clientSessionId;
}

/** SOPInstanceUID of the source's first slice, so the proxy can match its volume to our slice order. */
function firstSOPInstanceUID(source: SourceImage): string | undefined {
  const imageId = source.imageIds[0];
  if (!imageId) {
    return undefined;
  }
  return (
    metaData.get('instance', imageId)?.SOPInstanceUID ?? imageId.match(/\/instances\/([^/]+)/)?.[1]
  );
}

/** [slices, rows, columns] as the viewer sees the source; the proxy rejects a mismatched volume. */
function volumeShape(source: SourceImage): number[] | undefined {
  const imageId = source.imageIds[0];
  const pixel = imageId && metaData.get('imagePixelModule', imageId);
  return pixel?.rows && pixel?.columns
    ? [source.imageIds.length, pixel.rows, pixel.columns]
    : undefined;
}

type Mask = { data: Blob; fileName: string };

function post(source: SourceImage, params: Record<string, unknown>, mask?: Mask) {
  const formData = new FormData();
  formData.append(
    'params',
    JSON.stringify({
      ...params,
      studyInstanceUID: source.studyInstanceUID,
      firstSOPInstanceUID: firstSOPInstanceUID(source),
      volumeShape: volumeShape(source),
      clientSessionID: getClientSessionId(),
    })
  );
  if (mask) {
    formData.append('mask', mask.data, mask.fileName);
  }
  const url = `${BASE_URL}/infer/segmentation?image=${encodeURIComponent(source.seriesInstanceUID)}`;
  return axios.post(url, formData, { responseType: 'arraybuffer' });
}

function parseShape(value: unknown): [number, number, number] {
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value;
    if (Array.isArray(parsed) && parsed.length === 3) {
      return [Number(parsed[0]), Number(parsed[1]), Number(parsed[2])];
    }
  } catch {
    // fall through
  }
  return [0, 0, 0];
}

async function postForCrop(source: SourceImage, params: Record<string, unknown>, mask?: Mask) {
  const response = await post(source, params, mask);
  const { meta, seg } = parseMultipart(response.data, String(response.headers['content-type']));
  const cropShape = parseShape(meta.pred_crop_shape);
  const scope: PredictionCrop['scope'] =
    meta.pred_scope === 'full' ? 'full' : cropShape.every(n => n === 0) ? 'unchanged' : 'delta';
  const crop: PredictionCrop = {
    seg,
    scope,
    offset: parseShape(meta.pred_offset),
    fullShape: parseShape(meta.pred_full_shape),
    cropShape,
    flipped: meta.flipped === 'true',
    meta,
  };
  return crop;
}

/** Whether the nnInteractive backend is installed and reachable. */
export async function isAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/infer/availability`, { cache: 'no-store' });
    return response.ok && !!(await response.json())?.available;
  } catch {
    return false;
  }
}

/** True when the backend rejected because our session no longer exists (HTTP 409). */
export function isSessionExpiredError(error: any): boolean {
  return error?.response?.status === 409;
}

/**
 * Initialize (or reclaim) a backend session for the source series. The proxy
 * loads the DICOM series into the nnInteractive session on the first init.
 */
export async function createSession(source: SourceImage): Promise<void> {
  try {
    await post(source, { nninter: 'init' });
  } catch (error) {
    // The session may already exist for this browser (e.g. a duplicate init). If a
    // liveness probe says it is active, treat init as successful.
    if (!(await getSessionStatus(source).catch(() => false))) {
      throw error;
    }
  }
}

/** Non-creating liveness probe / browser heartbeat. Returns whether a session is active. */
export async function getSessionStatus(source: SourceImage): Promise<boolean> {
  const response = await axios.get(`${BASE_URL}/infer/session`, {
    params: {
      image: source.seriesInstanceUID,
      studyInstanceUID: source.studyInstanceUID,
      clientSessionID: getClientSessionId(),
    },
  });
  return !!response.data?.active;
}

/** Release the backend lease. Uses fetch+keepalive so it survives page unload. */
export function closeSession(source: SourceImage): void {
  const body = new FormData();
  body.append('image', source.seriesInstanceUID);
  body.append('studyInstanceUID', source.studyInstanceUID);
  body.append('clientSessionID', getClientSessionId());
  fetch(`${BASE_URL}/infer/close`, {
    method: 'POST',
    body,
    keepalive: true,
    credentials: 'include',
  }).catch(
    () => undefined // teardown is best effort
  );
}

/** Clear the backend target buffer / interaction history for the active object. */
export async function resetInteractions(source: SourceImage): Promise<void> {
  await post(source, { nninter: 'reset' });
}

/**
 * Upload the active object's full-volume mask so the backend adopts it as the
 * current object before refinement. `mask` is uint8, one byte per voxel, in
 * viewer slice order [z, y, x]. Gzipped: the mask is very sparse.
 */
export async function setActiveObjectMask(
  source: SourceImage,
  mask: Uint8Array
): Promise<PredictionCrop> {
  const gzipped = new Blob([mask]).stream().pipeThrough(new CompressionStream('gzip'));
  const data = await new Response(gzipped).blob();
  return postForCrop(source, { nninter: 'set_mask' }, { data, fileName: 'mask.raw.gz' });
}

/** Submit new prompt interactions. Only unsubmitted prompts should be passed; the backend dedups. */
export async function submitPrompts(
  source: SourceImage,
  prompts: PromptArrays,
  resetFirst: boolean
): Promise<PredictionCrop> {
  return postForCrop(source, { ...prompts, nninter: true, nninter_reset_first: resetFirst });
}

/** Undo the last accepted interaction. Returns the crop plus whether an undo actually ran. */
export async function undo(
  source: SourceImage
): Promise<{ crop: PredictionCrop; undone: boolean }> {
  const crop = await postForCrop(source, { nninter: 'undo' });
  return { crop, undone: crop.meta.undone === 'true' };
}
