// toolboxState: the small, transient UI/interaction state. Panels subscribe instead of polling.
// It holds NO object truth, server session id, or prompt history — only view/mode state.

import { createStore } from '../model/store';

interface ToolboxState {
  /** Run each prompt as soon as it is drawn. */
  liveMode: boolean;
  /** The next prompt or brush stroke is negative (erases). */
  negative: boolean;
  promptsVisible: boolean;
  manualCorrectionMode: boolean;
  /** Currently armed prompt/brush tool id, or 'none'. */
  tool: string;
  brushSize: number;
  /** The nnInteractive mode is the current OHIF mode. */
  modeActive: boolean;
}

const initialState: ToolboxState = {
  liveMode: true,
  negative: false,
  promptsVisible: true,
  manualCorrectionMode: false,
  tool: 'none',
  brushSize: 10,
  modeActive: false,
};

const store = createStore<ToolboxState>(initialState);

export const toolboxState = {
  get: store.get,
  set: store.set,
  subscribe: store.subscribe,
  reset: () => store.set(initialState),
};
