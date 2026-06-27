let liveMode = true;
let posNeg = false;
let refineNew = false;
let locked = false;
let promptsVisible = false;
let currentActiveSegment = 1;
let sessionActive = false;
let sessionSeries = '';
let manualCorrectionMode = false;

export const toolboxState = {
  getLiveMode: () => liveMode,
  setLiveMode: (enabled: boolean) => {
    liveMode = enabled;
  },
  getPosNeg: () => posNeg,
  setPosNeg: (enabled: boolean) => {
    posNeg = enabled;
  },
  getPromptsVisible: () => promptsVisible,
  setPromptsVisible: (visible: boolean) => {
    promptsVisible = visible;
  },
  getRefineNew: () => refineNew,
  setRefineNew: (enabled: boolean) => {
    refineNew = enabled;
    if (enabled) {
      toolboxState.setPosNeg(false);
    }
  },
  getLocked: () => locked,
  setLocked: (isLocked: boolean) => {
    locked = isLocked;
  },
  getCurrentActiveSegment: () => currentActiveSegment,
  setCurrentActiveSegment: (segment: number) => {
    currentActiveSegment = segment;
  },
  getSessionActive: () => sessionActive,
  setSessionActive: (active: boolean) => {
    sessionActive = active;
  },
  getSessionSeries: () => sessionSeries,
  setSessionSeries: (series: string) => {
    sessionSeries = series;
  },
  getManualCorrectionMode: () => manualCorrectionMode,
  setManualCorrectionMode: (enabled: boolean) => {
    manualCorrectionMode = enabled;
  },
};
