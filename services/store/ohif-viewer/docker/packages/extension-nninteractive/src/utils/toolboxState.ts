// toolboxState: the small, transient UI/interaction state (Ponytail InteractionState +
// DisplayState). It is now an observable store so panels subscribe instead of polling.
// It holds NO object truth, server session id, or prompt history — only view/mode state.

import { createStore, Unsubscribe } from '../model/store';

interface ToolboxState {
  liveMode: boolean;
  posNeg: boolean; // false = positive, true = negative
  refineNew: boolean;
  locked: boolean;
  promptsVisible: boolean;
  currentActiveSegment: number;
  sessionActive: boolean;
  sessionSeries: string;
  manualCorrectionMode: boolean;
  tool: string; // currently armed prompt/brush tool id, or 'none'
  brushSize: number;
}

const store = createStore<ToolboxState>({
  liveMode: true,
  posNeg: false,
  refineNew: false,
  locked: false,
  promptsVisible: true,
  currentActiveSegment: 1,
  sessionActive: false,
  sessionSeries: '',
  manualCorrectionMode: false,
  tool: 'none',
  brushSize: 10,
});

export const toolboxState = {
  subscribe: (listener: () => void): Unsubscribe => store.subscribe(listener),

  getLiveMode: () => store.get().liveMode,
  setLiveMode: (enabled: boolean) => store.set({ liveMode: enabled }),

  getPosNeg: () => store.get().posNeg,
  setPosNeg: (enabled: boolean) => store.set({ posNeg: enabled }),

  getPromptsVisible: () => store.get().promptsVisible,
  setPromptsVisible: (visible: boolean) => store.set({ promptsVisible: visible }),

  getRefineNew: () => store.get().refineNew,
  setRefineNew: (enabled: boolean) =>
    store.set(enabled ? { refineNew: true, posNeg: false } : { refineNew: false }),

  getLocked: () => store.get().locked,
  setLocked: (isLocked: boolean) => store.set({ locked: isLocked }),

  getCurrentActiveSegment: () => store.get().currentActiveSegment,
  setCurrentActiveSegment: (segment: number) => store.set({ currentActiveSegment: segment }),

  getSessionActive: () => store.get().sessionActive,
  setSessionActive: (active: boolean) => store.set({ sessionActive: active }),

  getSessionSeries: () => store.get().sessionSeries,
  setSessionSeries: (series: string) => store.set({ sessionSeries: series }),

  getManualCorrectionMode: () => store.get().manualCorrectionMode,
  setManualCorrectionMode: (enabled: boolean) => store.set({ manualCorrectionMode: enabled }),

  getTool: () => store.get().tool,
  setTool: (tool: string) => store.set({ tool }),

  getBrushSize: () => store.get().brushSize,
  setBrushSize: (brushSize: number) => store.set({ brushSize }),
};
