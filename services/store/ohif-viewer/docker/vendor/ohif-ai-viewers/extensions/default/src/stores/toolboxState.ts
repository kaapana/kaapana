// Simple global state for toolbox settings
// Default to true for live mode
let liveMode = true;
let posNeg = false;
let refineNew = false;
let textPromptReplaceNew = false; // Replace/New toggle for Text Prompt Segmentation
let selectedModel: 'nnInteractive' | 'sam2' | 'medsam2' | 'sam3' = 'nnInteractive'; // Model selection: nnInteractive, SAM2, MedSAM2, or SAM3
let locked = false;
let promptsVisible = false; // default: hide prompts after each inference; pencil toggle to always-show
let currentActiveSegment = 1;
let medgemmaResult: string | null = null;
let medgemmaInstruction: string = '';
let medgemmaQuery: string = '';
let medgemmaStartSlice: number | null = null;
let medgemmaEndSlice: number | null = null;
let geminiModel: string = 'gemini-3-flash-preview';
/** Gemini 3 thinking level: empty = API default; else low | medium | high (sent as gemini_thinking_level). */
let geminiThinkingLevel: '' | 'low' | 'medium' | 'high' = '';

/** Which VLM backend to use from the test toolbox (extend when adding more models). */
export type VlmProviderId =
  | 'medGemma'
  | 'gemini'
  | 'openai'
  | 'claude'
  | 'kimi'
  | 'qwen'
  | 'gemma'
  | 'vllm';

/** vLLM OpenAI-compatible server: served model family (empty = infer from model id). */
export type VllmFamilyId = '' | 'internvl' | 'qwen' | 'kimi' | 'gemma';

/** vLLM thinking: off (no InternVL system / no native thinking extras) or on. */
export type VllmThinkingLevel = 'off' | 'on';

/** Local MedGemma HF variant: ``1.5-4b`` → 1.5-4B IT; ``27b`` → ``google/medgemma-27b-it``. */
export type MedgemmaVariantId = '1.5-4b' | '27b';

let vlmProvider: VlmProviderId = 'medGemma';

let openaiModel = 'gpt-5.4';
let openaiReasoningEffort = 'none';

let claudeModel = 'claude-sonnet-4-20250514';
/** Empty = omit adaptive thinking; else sent as claude_thinking_effort. */
let claudeThinkingEffort: '' | 'low' | 'medium' | 'high' | 'max' = '';

let kimiModel = 'moonshotai/Kimi-K2.5:novita';
let kimiReasoningEnabled = true;

let qwenModel = 'Qwen/Qwen3.5-397B-A17B:novita';
let qwenThinkingEnabled = true;

let gemmaModel = 'google/gemma-4-31B-it:novita';
let gemmaThinkingEnabled = true;

let medgemmaVariant: MedgemmaVariantId = '1.5-4b';
let medgemmaThinkingEnabled = false;

/** OpenAI-compatible vLLM base URL (include /v1). */
let vllmBaseUrl = 'http://host.docker.internal:8000/v1';
let vllmFamily: VllmFamilyId = '';
let vllmThinkingLevel: VllmThinkingLevel = 'on';

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
        // Note: resetNninter should be called from the component/command that uses this state
         // When RefineNew is enabled and model is nnInteractive, reset nninter
         if (selectedModel === 'nnInteractive') {
          commandsManager?.run('resetNninter');
        }
        toolboxState.setPosNeg(false);
    }
  },
  getTextPromptReplaceNew: () => textPromptReplaceNew,
  setTextPromptReplaceNew: (enabled: boolean) => {
    textPromptReplaceNew = enabled;
  },
  // Model selection methods
  getSelectedModel: () => selectedModel,
  setSelectedModel: (model: 'nnInteractive' | 'sam2' | 'medsam2' | 'sam3') => {
    selectedModel = model;
  },
  // Legacy methods for backward compatibility (deprecated)
  getNnInterSam2: () => selectedModel === 'sam2',
  setNnInterSam2: (enabled: boolean) => {
    selectedModel = enabled ? 'sam2' : 'nnInteractive';
  },
  getMedSam2: () => selectedModel === 'medsam2',
  setMedSam2: (enabled: boolean) => {
    selectedModel = enabled ? 'medsam2' : 'nnInteractive';
  },
  getLocked: () => locked,
  setLocked: (isLocked: boolean) => {
    locked = isLocked;
  },
  getCurrentActiveSegment: () => currentActiveSegment,
  setCurrentActiveSegment: (segment: number) => {
    currentActiveSegment = segment;
  },
  getMedgemmaResult: () => medgemmaResult,
  setMedgemmaResult: (result: string | null) => {
    medgemmaResult = result;
  },
  getMedgemmaInstruction: () => medgemmaInstruction,
  setMedgemmaInstruction: (instruction: string) => {
    medgemmaInstruction = instruction;
  },
  getMedgemmaQuery: () => medgemmaQuery,
  setMedgemmaQuery: (query: string) => {
    medgemmaQuery = query;
  },
  getMedgemmaStartSlice: () => medgemmaStartSlice,
  setMedgemmaStartSlice: (startSlice: number | null) => {
    medgemmaStartSlice = startSlice;
  },
  getMedgemmaEndSlice: () => medgemmaEndSlice,
  setMedgemmaEndSlice: (endSlice: number | null) => {
    medgemmaEndSlice = endSlice;
  },
  getGeminiModel: () => geminiModel,
  setGeminiModel: (model: string) => {
    geminiModel = model;
  },
  getGeminiThinkingLevel: (): '' | 'low' | 'medium' | 'high' => geminiThinkingLevel,
  setGeminiThinkingLevel: (level: '' | 'low' | 'medium' | 'high') => {
    geminiThinkingLevel = level;
  },
  getVlmProvider: (): VlmProviderId => vlmProvider,
  setVlmProvider: (provider: VlmProviderId) => {
    vlmProvider = provider;
  },
  getMedgemmaVariant: (): MedgemmaVariantId => medgemmaVariant,
  setMedgemmaVariant: (variant: MedgemmaVariantId) => {
    medgemmaVariant = variant;
  },
  getMedgemmaThinkingEnabled: () => medgemmaThinkingEnabled,
  setMedgemmaThinkingEnabled: (enabled: boolean) => {
    medgemmaThinkingEnabled = enabled;
  },
  getOpenaiModel: () => openaiModel,
  setOpenaiModel: (model: string) => {
    openaiModel = model;
  },
  getOpenaiReasoningEffort: () => openaiReasoningEffort,
  setOpenaiReasoningEffort: (effort: string) => {
    openaiReasoningEffort = effort;
  },
  getClaudeModel: () => claudeModel,
  setClaudeModel: (model: string) => {
    claudeModel = model;
  },
  getClaudeThinkingEffort: (): '' | 'low' | 'medium' | 'high' | 'max' =>
    claudeThinkingEffort,
  setClaudeThinkingEffort: (level: '' | 'low' | 'medium' | 'high' | 'max') => {
    claudeThinkingEffort = level;
  },
  getKimiModel: () => kimiModel,
  setKimiModel: (model: string) => {
    kimiModel = model;
  },
  getKimiReasoningEnabled: () => kimiReasoningEnabled,
  setKimiReasoningEnabled: (enabled: boolean) => {
    kimiReasoningEnabled = enabled;
  },
  getQwenModel: () => qwenModel,
  setQwenModel: (model: string) => {
    qwenModel = model;
  },
  getQwenThinkingEnabled: () => qwenThinkingEnabled,
  setQwenThinkingEnabled: (enabled: boolean) => {
    qwenThinkingEnabled = enabled;
  },
  getGemmaModel: () => gemmaModel,
  setGemmaModel: (model: string) => {
    gemmaModel = model;
  },
  getGemmaThinkingEnabled: () => gemmaThinkingEnabled,
  setGemmaThinkingEnabled: (enabled: boolean) => {
    gemmaThinkingEnabled = enabled;
  },
  getVllmBaseUrl: () => vllmBaseUrl,
  setVllmBaseUrl: (url: string) => {
    vllmBaseUrl = url;
  },
  getVllmFamily: (): VllmFamilyId => vllmFamily,
  setVllmFamily: (family: VllmFamilyId) => {
    vllmFamily = family;
  },
  getVllmThinkingLevel: (): VllmThinkingLevel => vllmThinkingLevel,
  setVllmThinkingLevel: (level: VllmThinkingLevel) => {
    vllmThinkingLevel = level;
  },
};
