// sessionModel: the nnInteractive session lifecycle for one source series.
//
// Holds SessionState (status + source identity + a monotonic generation used as a
// stale-response guard) and orchestrates serverApi for init/close/heartbeat. Owns no
// masks, no active segment, no prompt geometry — only whether requests may be sent.

import { createStore } from './store';
import * as serverApi from './serverApi';
import { getActiveSource, sameSource } from './imageModel';
import { SessionStatus, SourceImage } from './types';

interface SessionState {
  status: SessionStatus;
  source: SourceImage | null;
  /** Bumped on every init/reset. Responses tagged with an older generation are stale. */
  generation: number;
  lastError: string | null;
}

const store = createStore<SessionState>({
  status: 'idle',
  source: null,
  generation: 0,
  lastError: null,
});

export const sessionState = {
  get: store.get,
  subscribe: store.subscribe,
};

export function getSource(): SourceImage | null {
  return store.get().source;
}

export function getGeneration(): number {
  return store.get().generation;
}

export function isReady(): boolean {
  return store.get().status === 'ready';
}

/** True when the ready session still matches the currently displayed series. */
export function isReadyForActive(servicesManager: any): boolean {
  const state = store.get();
  if (state.status !== 'ready') {
    return false;
  }
  return sameSource(state.source, getActiveSource(servicesManager));
}

/**
 * Initialize a backend session for the active source series. Idempotent per series:
 * re-initializing the same ready series is a no-op.
 */
export async function initialize(servicesManager: any): Promise<boolean> {
  const source = getActiveSource(servicesManager);
  if (!source) {
    store.set({ status: 'error', lastError: 'No source image series is active.' });
    return false;
  }

  if (store.get().status === 'ready' && sameSource(store.get().source, source)) {
    return true;
  }
  if (store.get().status === 'initializing') {
    return false;
  }

  store.update(prev => ({
    status: 'initializing',
    source,
    lastError: null,
    generation: prev.generation + 1,
  }));

  try {
    await serverApi.createSession(source);
    store.set({ status: 'ready', source });
    return true;
  } catch (error: any) {
    store.set({ status: 'error', lastError: String(error?.message ?? error) });
    return false;
  }
}

/** Heartbeat: confirm the backend still holds our session; mark expired otherwise. */
export async function heartbeat(): Promise<boolean> {
  const source = store.get().source;
  if (!source || store.get().status !== 'ready') {
    return false;
  }
  try {
    const active = await serverApi.getSessionStatus(source);
    if (!active) {
      store.set({ status: 'expired' });
    }
    return active;
  } catch {
    return true; // transient network error — keep the session and retry next tick
  }
}

/** Called when a request returns HTTP 409 (session gone on the backend). */
export function markExpired(): void {
  if (store.get().status === 'ready') {
    store.set({ status: 'expired' });
  }
}

/** Bump the generation (used after a backend reset invalidates in-flight responses). */
export function bumpGeneration(): void {
  store.update(prev => ({ generation: prev.generation + 1 }));
}

export function close(): void {
  const source = store.get().source;
  if (source) {
    serverApi.closeSession(source);
  }
  store.set({ status: 'idle', source: null });
}
