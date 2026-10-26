// serverApi: the single transport facade to the nnInteractive backend.
//
// Nothing else in the plugin knows whether requests go through the Kaapana proxy
// or a direct server. Callers pass source-voxel coordinates and receive typed
// prediction crops; they never build URLs, headers, or multipart bodies.
//
// Protocol (see the FastAPI proxy): POST /nninteractive/infer/segmentation?image=<seriesUID>
// with a multipart form whose `params` field is a JSON object carrying the
// `nninter` discriminator (init | true | undo | reset | set_mask), studyInstanceUID,
// clientSessionID and the prompt arrays. Responses are multipart (meta JSON + seg
// bytes); meta carries pred_scope/pred_offset/pred_full_shape/pred_crop_shape/flipped.

import axios from 'axios';

import { parseMultipart } from '../utils/multipart';
import {
  NN_BASE_URL,
  NN_CLIENT_SESSION_KEY,
  PredictionCrop,
  PromptArrays,
  SourceImage,
} from './types';

let cachedClientSessionId: string | undefined;

export function getClientSessionId(): string {
  if (cachedClientSessionId) {
    return cachedClientSessionId;
  }
  try {
    const stored = window.sessionStorage.getItem(NN_CLIENT_SESSION_KEY);
    if (stored) {
      cachedClientSessionId = stored;
      return stored;
    }
  } catch {
    // sessionStorage may be unavailable; fall through to a runtime-only id.
  }

  const generated =
    (globalThis.crypto as any)?.randomUUID?.() ??
    `nn-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e9).toString(36)}`;
  cachedClientSessionId = generated;
  try {
    window.sessionStorage.setItem(NN_CLIENT_SESSION_KEY, generated);
  } catch {
    // ignore
  }
  return generated;
}

function segmentationUrl(series: string): string {
  return `${NN_BASE_URL}/infer/segmentation?image=${encodeURIComponent(series)}&output=dicom_seg`;
}

function withClientSession(url: string): string {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}clientSessionID=${encodeURIComponent(getClientSessionId())}`;
}

const BASE_PARAMS = {
  largest_cc: false,
  result_extension: '.nii.gz',
  result_dtype: 'uint16',
  result_compress: false,
  restore_label_idx: false,
};

function buildFormData(params: Record<string, unknown>, file?: { name: string; data: Blob; fileName: string }) {
  const formData = new FormData();
  formData.append(
    'params',
    JSON.stringify({
      ...params,
      clientSessionID: getClientSessionId(),
    })
  );
  if (file) {
    formData.append(file.name, file.data, file.fileName);
  }
  return formData;
}

function toPredictionCrop(meta: Record<string, any>, seg: Uint8Array): PredictionCrop {
  const parse = (value: any, fallback: number[]): [number, number, number] => {
    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value;
      if (Array.isArray(parsed) && parsed.length === 3) {
        return [Number(parsed[0]), Number(parsed[1]), Number(parsed[2])];
      }
    } catch {
      // fall through
    }
    return fallback as [number, number, number];
  };

  const cropShape = parse(meta?.pred_crop_shape, [0, 0, 0]);
  const scopeRaw = String(meta?.pred_scope || '').toLowerCase();
  const scope: PredictionCrop['scope'] =
    scopeRaw === 'full'
      ? 'full'
      : cropShape[0] === 0 && cropShape[1] === 0 && cropShape[2] === 0
        ? 'unchanged'
        : 'delta';

  return {
    seg,
    scope,
    offset: parse(meta?.pred_offset, [0, 0, 0]),
    fullShape: parse(meta?.pred_full_shape, [0, 0, 0]),
    cropShape,
    flipped: String(meta?.flipped).toLowerCase() === 'true',
    meta,
  };
}

async function postForCrop(
  series: string,
  params: Record<string, unknown>,
  file?: { name: string; data: Blob; fileName: string }
): Promise<PredictionCrop> {
  const response = await axios.post(segmentationUrl(series), buildFormData(params, file), {
    responseType: 'arraybuffer',
    headers: { accept: 'application/octet-stream' },
  });
  const { meta, seg } = await parseMultipart(response.data, response.headers['content-type'], {
    allowEmptySeg: true,
  });
  return toPredictionCrop(meta, seg);
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
  const params = { ...BASE_PARAMS, studyInstanceUID: source.studyInstanceUID, nninter: 'init' };
  try {
    const response = await axios.post(segmentationUrl(source.seriesInstanceUID), buildFormData(params), {
      responseType: 'arraybuffer',
      headers: { accept: 'application/json, multipart/form-data' },
    });
    if (response.status !== 200) {
      throw new Error(`nnInteractive init failed with status ${response.status}`);
    }
  } catch (error) {
    // The session may already exist for this browser (e.g. a duplicate init). If a
    // liveness probe says it is active, treat init as successful.
    const active = await getSessionStatus(source).catch(() => false);
    if (!active) {
      throw error;
    }
  }
}

/** Non-creating liveness probe / browser heartbeat. Returns whether a session is active. */
export async function getSessionStatus(source: SourceImage): Promise<boolean> {
  const url = withClientSession(
    `${NN_BASE_URL}/infer/session?image=${encodeURIComponent(source.seriesInstanceUID)}&studyInstanceUID=${encodeURIComponent(source.studyInstanceUID)}`
  );
  const response = await axios.get(url);
  return !!response?.data?.active;
}

/** Release the backend lease. Uses fetch+keepalive so it survives page unload. */
export function closeSession(source: SourceImage): void {
  const url = `${NN_BASE_URL}/infer/close`;
  const body = new FormData();
  body.append('image', source.seriesInstanceUID);
  body.append('studyInstanceUID', source.studyInstanceUID);
  body.append('clientSessionID', getClientSessionId());
  try {
    fetch(url, { method: 'POST', body, keepalive: true, credentials: 'include' }).catch(() => {});
  } catch {
    // ignore — teardown is best effort
  }
}

/** Clear the backend target buffer / interaction history for the active object. */
export async function resetInteractions(source: SourceImage): Promise<void> {
  const params = { ...BASE_PARAMS, studyInstanceUID: source.studyInstanceUID, nninter: 'reset' };
  await axios.post(segmentationUrl(source.seriesInstanceUID), buildFormData(params), {
    responseType: 'arraybuffer',
    headers: { accept: 'application/json, multipart/form-data' },
  });
}

/**
 * Upload the active object's full-volume mask so the backend adopts it as the
 * current object before refinement. `mask` is uint8, one byte per voxel, in
 * viewer slice order [z, y, x]. Gzipped when the browser supports CompressionStream.
 */
export async function setActiveObjectMask(source: SourceImage, mask: Uint8Array): Promise<PredictionCrop> {
  let blob: Blob = new Blob([mask]);
  let fileName = 'mask.raw';
  if (typeof (globalThis as any).CompressionStream !== 'undefined') {
    try {
      blob = await new Response(
        blob.stream().pipeThrough(new (globalThis as any).CompressionStream('gzip'))
      ).blob();
      fileName = 'mask.raw.gz';
    } catch {
      blob = new Blob([mask]);
      fileName = 'mask.raw';
    }
  }
  const params = { ...BASE_PARAMS, studyInstanceUID: source.studyInstanceUID, nninter: 'set_mask' };
  return postForCrop(source.seriesInstanceUID, params, { name: 'mask', data: blob, fileName });
}

/** Submit new prompt interactions. Only unsubmitted prompts should be passed; the backend dedups. */
export async function submitPrompts(
  source: SourceImage,
  prompts: PromptArrays,
  resetFirst: boolean
): Promise<PredictionCrop> {
  const params = {
    ...BASE_PARAMS,
    studyInstanceUID: source.studyInstanceUID,
    ...prompts,
    nninter: true,
    nninter_reset_first: resetFirst,
  };
  return postForCrop(source.seriesInstanceUID, params);
}

/** Undo the last accepted interaction. Returns the crop plus whether an undo actually ran. */
export async function undo(source: SourceImage): Promise<{ crop: PredictionCrop; undone: boolean }> {
  const params = { ...BASE_PARAMS, studyInstanceUID: source.studyInstanceUID, nninter: 'undo' };
  const crop = await postForCrop(source.seriesInstanceUID, params);
  return { crop, undone: String(crop.meta?.undone).toLowerCase() === 'true' };
}
