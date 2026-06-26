import React, { useState, useEffect, useRef } from 'react';
import { Icons, PanelSection, ToolSettings, Switch, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Button, Input } from '@ohif/ui-next';
import { Lock, LockOpen } from 'lucide-react';
import { useSystem, useToolbar } from '@ohif/core';
import classnames from 'classnames';
import { useTranslation } from 'react-i18next';
import {
  toolboxState,
  type VlmProviderId,
  type VllmFamilyId,
  type VllmThinkingLevel,
  type MedgemmaVariantId,
} from '../stores/toolboxState';

interface ButtonProps {
  isActive?: boolean;
  options?: unknown;
}

/**
 * A toolbox is a collection of buttons and commands that they invoke, used to provide
 * custom control panels to users. This component is a generic UI component that
 * interacts with services and commands in a generic fashion. While it might
 * seem unconventional to import it from the UI and integrate it into the JSX,
 * it belongs in the UI components as there isn't anything in this component that
 * couldn't be used for a completely different type of app. It plays a crucial
 * role in enhancing the app with a toolbox by providing a way to integrate
 * and display various tools and their corresponding options
 */
export function Toolbox({ buttonSectionId, title, defaultOpen = true }: { buttonSectionId: string; title: string; defaultOpen?: boolean }) {
  const { servicesManager, commandsManager } = useSystem();
  const { t } = useTranslation();

  const { toolbarService, customizationService, segmentationService, viewportGridService, measurementService } = servicesManager.services;
  const onInteractionRef = React.useRef<((args: { itemId: string }) => void) | null>(null);
  const isAIToolBox = buttonSectionId === 'aiToolBox';
  const isTextPromptToolbox = buttonSectionId === 'textPromptSegmentationToolbox';
  const isTestMedgemmaToolbox = buttonSectionId === 'testMedgemmaToolbox';
  const [showConfig, setShowConfig] = useState(false);
  const [isLocked, setIsLocked] = useState(toolboxState.getLocked());
  const hotkeysDisabled = isAIToolBox && isLocked;

  // Local state for UI updates
  const [liveMode, setLiveMode] = useState(toolboxState.getLiveMode());
  const [posNeg, setPosNeg] = useState(toolboxState.getPosNeg());
  const [textPromptReplaceNew, setTextPromptReplaceNew] = useState(toolboxState.getTextPromptReplaceNew());
  const [selectedModel, setSelectedModel] = useState<'nnInteractive' | 'sam2' | 'medsam2' | 'sam3'>(toolboxState.getSelectedModel());
  const [medgemmaResult, setMedgemmaResult] = useState(toolboxState.getMedgemmaResult());
  const [medgemmaInstruction, setMedgemmaInstruction] = useState(toolboxState.getMedgemmaInstruction());
  const [medgemmaQuery, setMedgemmaQuery] = useState(toolboxState.getMedgemmaQuery());
  const [medgemmaStartSlice, setMedgemmaStartSlice] = useState<number | null>(toolboxState.getMedgemmaStartSlice());
  const [medgemmaEndSlice, setMedgemmaEndSlice] = useState<number | null>(toolboxState.getMedgemmaEndSlice());
  const [geminiModel, setGeminiModel] = useState(toolboxState.getGeminiModel());
  const [geminiThinkingLevel, setGeminiThinkingLevel] = useState<
    '' | 'low' | 'medium' | 'high'
  >(toolboxState.getGeminiThinkingLevel());
  const [openaiModel, setOpenaiModel] = useState(toolboxState.getOpenaiModel());
  const [openaiReasoningEffort, setOpenaiReasoningEffort] = useState(
    toolboxState.getOpenaiReasoningEffort()
  );
  const [claudeModel, setClaudeModel] = useState(toolboxState.getClaudeModel());
  const [claudeThinkingEffort, setClaudeThinkingEffort] = useState(
    toolboxState.getClaudeThinkingEffort()
  );
  const [kimiModel, setKimiModel] = useState(toolboxState.getKimiModel());
  const [kimiReasoningEnabled, setKimiReasoningEnabled] = useState(
    toolboxState.getKimiReasoningEnabled()
  );
  const [qwenModel, setQwenModel] = useState(toolboxState.getQwenModel());
  const [qwenThinkingEnabled, setQwenThinkingEnabled] = useState(
    toolboxState.getQwenThinkingEnabled()
  );
  const [gemmaModel, setGemmaModel] = useState(toolboxState.getGemmaModel());
  const [gemmaThinkingEnabled, setGemmaThinkingEnabled] = useState(
    toolboxState.getGemmaThinkingEnabled()
  );
  const [vllmBaseUrl, setVllmBaseUrl] = useState(toolboxState.getVllmBaseUrl());
  const [vllmFamily, setVllmFamily] = useState<VllmFamilyId>(toolboxState.getVllmFamily());
  const [vllmThinkingLevel, setVllmThinkingLevel] = useState<VllmThinkingLevel>(
    toolboxState.getVllmThinkingLevel()
  );
  const [vlmProvider, setVlmProvider] = useState(toolboxState.getVlmProvider());
  const [medgemmaVariant, setMedgemmaVariant] = useState<MedgemmaVariantId>(
    toolboxState.getMedgemmaVariant()
  );
  const [medgemmaThinkingEnabled, setMedgemmaThinkingEnabled] = useState(
    toolboxState.getMedgemmaThinkingEnabled()
  );

  // Sync VLM toolbox state from toolboxState
  useEffect(() => {
    if (isTestMedgemmaToolbox) {
      const interval = setInterval(() => {
        const result = toolboxState.getMedgemmaResult();
        const instruction = toolboxState.getMedgemmaInstruction();
        const query = toolboxState.getMedgemmaQuery();
        const startSlice = toolboxState.getMedgemmaStartSlice();
        const endSlice = toolboxState.getMedgemmaEndSlice();
        const gm = toolboxState.getGeminiModel();
        const gtl = toolboxState.getGeminiThinkingLevel();
        const oam = toolboxState.getOpenaiModel();
        const oare = toolboxState.getOpenaiReasoningEffort();
        const cm = toolboxState.getClaudeModel();
        const cte = toolboxState.getClaudeThinkingEffort();
        const km = toolboxState.getKimiModel();
        const kre = toolboxState.getKimiReasoningEnabled();
        const qm = toolboxState.getQwenModel();
        const qte = toolboxState.getQwenThinkingEnabled();
        const gmm = toolboxState.getGemmaModel();
        const gte = toolboxState.getGemmaThinkingEnabled();
        const vbu = toolboxState.getVllmBaseUrl();
        const vf = toolboxState.getVllmFamily();
        const vtl = toolboxState.getVllmThinkingLevel();
        const vp = toolboxState.getVlmProvider();
        const mv = toolboxState.getMedgemmaVariant();
        const mte = toolboxState.getMedgemmaThinkingEnabled();
        setMedgemmaResult(result);
        setMedgemmaInstruction(instruction);
        setMedgemmaQuery(query);
        setMedgemmaStartSlice(startSlice);
        setMedgemmaEndSlice(endSlice);
        setGeminiModel(gm);
        setGeminiThinkingLevel(gtl);
        setOpenaiModel(oam);
        setOpenaiReasoningEffort(oare);
        setClaudeModel(cm);
        setClaudeThinkingEffort(cte);
        setKimiModel(km);
        setKimiReasoningEnabled(kre);
        setQwenModel(qm);
        setQwenThinkingEnabled(qte);
        setGemmaModel(gmm);
        setGemmaThinkingEnabled(gte);
        setVllmBaseUrl(vbu);
        setVllmFamily(vf);
        setVllmThinkingLevel(vtl);
        setVlmProvider(vp);
        setMedgemmaVariant(mv);
        setMedgemmaThinkingEnabled(mte);
      }, 100); // Check every 100ms for updates
      return () => clearInterval(interval);
    }
  }, [isTestMedgemmaToolbox]);

  // Sync local state with global state changes
  useEffect(() => {
    const updateLocalState = () => {
      setLiveMode(toolboxState.getLiveMode());
      setPosNeg(toolboxState.getPosNeg());
      setTextPromptReplaceNew(toolboxState.getTextPromptReplaceNew());
      setSelectedModel(toolboxState.getSelectedModel());
      setIsLocked(toolboxState.getLocked());
    };

    // Update immediately
    updateLocalState();

    // Set up an interval to check for changes (since toolboxState doesn't have events)
    const interval = setInterval(updateLocalState, 100);

    return () => {
      clearInterval(interval);
      // Reset volatile interaction state when the user leaves the viewer (e.g. back to study list).
      // This ensures the next mount always reads the default (positive) regardless of series UID.
      toolboxState.setPosNeg(false);
    };
  }, []);

  // Consolidated keyboard hotkey handler (AI toolbox only)
  // Q = Live Mode, T = Pos/Neg, P = Point, B = BBox, S = Scribble, L = Lasso
  // M = Add Segment, R = Reset Segment, O = Show/Hide Prompts
  useEffect(() => {
    if (!isAIToolBox || hotkeysDisabled) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isInputField = activeElement?.tagName === 'INPUT' ||
                           activeElement?.tagName === 'TEXTAREA' ||
                           (activeElement as HTMLElement)?.contentEditable === 'true';
      if (isInputField) return;

      switch (event.key.toLowerCase()) {
        case 'q': {
          event.preventDefault();
          event.stopPropagation();
          const newLiveMode = !toolboxState.getLiveMode();
          setLiveMode(newLiveMode);
          toolboxState.setLiveMode(newLiveMode);
          break;
        }
        case 't': {
          event.preventDefault();
          event.stopPropagation();
          const newPosNeg = !toolboxState.getPosNeg();
          setPosNeg(newPosNeg);
          toolboxState.setPosNeg(newPosNeg);
          break;
        }
        case 'p':
          event.preventDefault();
          event.stopPropagation();
          onInteractionRef.current?.({ itemId: 'Probe2' });
          break;
        case 'b':
          event.preventDefault();
          event.stopPropagation();
          onInteractionRef.current?.({ itemId: 'RectangleROI2' });
          break;
        case 's':
          event.preventDefault();
          event.stopPropagation();
          onInteractionRef.current?.({ itemId: 'PlanarFreehandROI2' });
          break;
        case 'l':
          event.preventDefault();
          event.stopPropagation();
          onInteractionRef.current?.({ itemId: 'PlanarFreehandROI3' });
          break;
        case 'm': {
          event.preventDefault();
          event.stopPropagation();
          const { activeViewportId: avId } = viewportGridService.getState();
          const activeSeg = segmentationService.getActiveSegmentation(avId)
            ?? segmentationService.getSegmentations()?.[0];
          if (activeSeg?.segmentationId) {
            commandsManager.run('addSegment', { segmentationId: activeSeg.segmentationId });
            // Always start fresh in positive mode
            if (toolboxState.getPosNeg()) {
              toolboxState.setPosNeg(false);
            }
          }
          break;
        }
        case 'r': {
          event.preventDefault();
          event.stopPropagation();
          const { activeViewportId: avId } = viewportGridService.getState();
          const activeSeg = segmentationService.getActiveSegmentation(avId);
          const activeSeg2 = segmentationService.getActiveSegment(avId);
          if (activeSeg?.segmentationId && activeSeg2?.segmentIndex != null) {
            commandsManager.run('resetSegment', {
              segmentationId: activeSeg.segmentationId,
              segmentIndex: activeSeg2.segmentIndex,
            });
          }
          break;
        }
        case 'o': {
          event.preventDefault();
          event.stopPropagation();
          const next = !toolboxState.getPromptsVisible();
          toolboxState.setPromptsVisible(next);
          const AI_PROMPT_TOOLS = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'];
          const uids = measurementService
            .getMeasurements()
            .filter(m => AI_PROMPT_TOOLS.includes(m.toolName))
            .map(m => m.uid);
          measurementService.toggleVisibilityMeasurementMany(uids, next);
          break;
        }
        case 'z': {
          if (event.ctrlKey && !event.shiftKey) {
            event.preventDefault();
            event.stopPropagation();
            commandsManager.run('undoNninter');
          }
          break;
        }
        case 'delete': {
          event.preventDefault();
          event.stopPropagation();
          const { activeViewportId: avId } = viewportGridService.getState();
          const activeSeg = segmentationService.getActiveSegmentation(avId);
          const activeSeg2 = segmentationService.getActiveSegment(avId);
          if (activeSeg?.segmentationId && activeSeg2?.segmentIndex != null) {
            const { segmentationId } = activeSeg;
            const { segmentIndex } = activeSeg2;
            const measurementUIDs = measurementService
              .getMeasurements()
              .filter(m => m?.metadata?.segmentationId === segmentationId && m?.metadata?.SegmentNumber === segmentIndex)
              .map(m => m?.uid);
            if (measurementUIDs.length > 0) measurementService.removeMany(measurementUIDs);
            commandsManager.run('resetNninter', { clearMeasurements: false });
            commandsManager.run('deleteSegment', { segmentationId, segmentIndex });
          }
          break;
        }
      }
    };

    // Use capture phase so this fires before Mousetrap (bubble phase), preventing
    // global hotkey bindings from also firing for keys we own in the AI toolbox.
    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [hotkeysDisabled, isAIToolBox]);


  // When locked, force Pan tool active, disable live prompts, and collapse section
  useEffect(() => {
    if (isLocked) {
      try {
        // Disable live mode to avoid unintended inference
        if (liveMode) {
          setLiveMode(false);
          toolboxState.setLiveMode(false);
        }
        // Activate Pan tool
        commandsManager?.run?.('setToolActive', { toolName: 'Pan' });
      } catch (e) {
        // no-op
      }
    }
  }, [isLocked]);


  const { toolbarButtons: toolboxSections, onInteraction } = useToolbar({
    servicesManager,
    buttonSection: buttonSectionId,
  });
  onInteractionRef.current = onInteraction;

  if (!toolboxSections.length) {
    return null;
  }

  // Ensure we have proper button sections at the top level.
  if (!toolboxSections.every(section => section.componentProps.buttonSection)) {
    throw new Error(
      'Toolbox accepts only button sections at the top level, not buttons. Create at least one button section.'
    );
  }

  // Helper to check a list of buttons for an active tool.
  const findActiveOptions = (buttons: any[]): unknown => {
    for (const tool of buttons) {
      if (tool.componentProps.isActive) {
        return tool.componentProps.options;
      }
      if (tool.componentProps.buttonSection) {
        const nestedButtons = toolbarService.getButtonPropsInButtonSection(
          tool.componentProps.buttonSection
        ) as ButtonProps[];
        const activeNested = nestedButtons.find(nested => nested.isActive);
        if (activeNested) {
          return activeNested.options;
        }
      }
    }
    return null;
  };

  // Look for active tool options across all sections.
  const activeToolOptions = toolboxSections.reduce((activeOptions, section) => {
    if (activeOptions) {
      return activeOptions;
    }
    const sectionId = section.componentProps.buttonSection;
    const buttons = toolbarService.getButtonSection(sectionId);
    return findActiveOptions(buttons);
  }, null);

  // Define the interaction handler once.
  const handleInteraction = ({ itemId }: { itemId: string }) => {
    if (isAIToolBox && isLocked && itemId !== 'Pan') {
      // Prevent tool changes when locked; keep Pan active
      commandsManager?.run?.('setToolActive', { toolName: 'Pan' });
      return;
    }
    onInteraction?.({ itemId });
  };

  const CustomConfigComponent = customizationService.getCustomization(`${buttonSectionId}.config`);
  const shouldCollapse = isAIToolBox && isLocked;

  return (
    <PanelSection key={isAIToolBox ? `toolbox-${isLocked}` : buttonSectionId} defaultOpen={defaultOpen && !shouldCollapse}>
      <PanelSection.Header 
        className="flex items-center justify-between"
      >
        <span className={classnames("flex items-center gap-2", { 
          "pointer-events-none": shouldCollapse 
        })}>
          <span className="pointer-events-auto">{t(title)}</span>
          {isAIToolBox && (
            <button
              type="button"
              className={classnames('ml-auto h-5 w-5 text-primary hover:opacity-80 pointer-events-auto cursor-pointer')}
              onClick={e => {
                e.stopPropagation();
                const next = !isLocked;
                setIsLocked(next);
                toolboxState.setLocked(next);
                if (next) {
                  commandsManager?.run?.('setToolActive', { toolName: 'Pan' });
                }
              }}
              aria-label={isLocked ? 'Unlock tools' : 'Lock tools'}
              title={isLocked ? 'Unlock tools' : 'Lock tools'}
            >
              {isLocked ? <Lock className="h-4 w-4" /> : <LockOpen className="h-4 w-4" />}
            </button>
          )}
        </span>
        {CustomConfigComponent && (
          <div className="ml-auto mr-2">
            <Icons.Settings
              className="text-primary h-4 w-4"
              onClick={e => {
                e.stopPropagation();
                setShowConfig(!showConfig);
              }}
            />
          </div>
        )}
      </PanelSection.Header>

      {!shouldCollapse && (
      <PanelSection.Content className="bg-muted flex-shrink-0 border-none">
        {showConfig && <CustomConfigComponent />}
        {toolboxSections.map(section => {
          const sectionId = section.componentProps.buttonSection;
          const buttons = toolbarService.getButtonSection(sectionId) as any[];

          return (
            <React.Fragment key={sectionId}>
              {isAIToolBox && (
                <div className="flex justify-center items-center gap-4 py-2 px-1">
                   <div className="flex items-center gap-2">
                     <Label htmlFor="live-mode">Live Mode [Q]</Label>
                     <Switch
                       id="live-mode"
                       checked={liveMode}
                       onCheckedChange={(checked) => {
                        setLiveMode(checked);
                        toolboxState.setLiveMode(checked);
                        console.log('Live mode:', checked);
                       }}
                     />
                   </div>
                   <div className="flex items-center gap-2">
                     <Label htmlFor="pos-neg">Pos/Neg [T]</Label>
                     <Switch
                       id="pos-neg"
                       checked={posNeg}
                       onCheckedChange={(checked) => {
                        setPosNeg(checked);
                        toolboxState.setPosNeg(checked);
                        console.log('Pos/Neg:', checked);
                      }}
                     />
                   </div>
                   <div className="flex items-center gap-2">
                     <Label htmlFor="model-selection">Model</Label>
                     <Select
                       value={selectedModel}
                       onValueChange={(value) => {
                         const model = value as 'nnInteractive' | 'sam2' | 'medsam2' | 'sam3';
                         setSelectedModel(model);
                         toolboxState.setSelectedModel(model);
                         console.log('Model selection:', model);
                       }}
                     >
                       <SelectTrigger id="model-selection" className="w-[140px]">
                         <SelectValue placeholder="Select model" />
                       </SelectTrigger>
                       <SelectContent>
                         <SelectItem value="nnInteractive">nnInteractive</SelectItem>
                         <SelectItem value="sam2">SAM2</SelectItem>
                         <SelectItem value="medsam2">MedSAM2</SelectItem>
                         <SelectItem value="sam3">SAM3</SelectItem>
                       </SelectContent>
                    </Select>
                   </div>
                 </div>
                )}
              {isTextPromptToolbox && (
                <div className="flex justify-center items-center gap-4 py-2 px-1">
                   <div className="flex items-center gap-2">
                     <Label htmlFor="replace-new">Replace/New</Label>
                     <Switch
                       id="replace-new"
                       checked={textPromptReplaceNew}
                       onCheckedChange={(checked) => {
                        setTextPromptReplaceNew(checked);
                        toolboxState.setTextPromptReplaceNew(checked);
                        console.log('Replace/New:', checked);
                      }}
                     />
                   </div>
                 </div>
                )}
              <div
                className="bg-muted flex flex-wrap space-x-2 py-2 px-1"
              >
              {buttons.map(tool => {
                if (!tool) {
                  return null;
                }
                const { id, Component, componentProps } = tool;

                // Hide testMedgemma button since we have input fields in the Toolbox
                if (isTestMedgemmaToolbox && id === 'testMedgemma') {
                  return null;
                }

                return (
                  <div
                    key={id}
                    className={classnames('ml-1')}
                  >
                    <Component
                      {...componentProps}
                      id={id}
                      onInteraction={handleInteraction}
                      size="toolbox"
                      servicesManager={servicesManager}
                    />
                  </div>
                );
              })}
            </div>
            {isTestMedgemmaToolbox && (
              <div className="flex flex-col gap-3 py-3 px-2 border-t border-primary/20">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="vlm-provider" className="text-sm font-semibold">
                    VLM model
                  </Label>
                  <Select
                    value={vlmProvider}
                    onValueChange={(value: VlmProviderId) => {
                      setVlmProvider(value);
                      toolboxState.setVlmProvider(value);
                    }}
                  >
                    <SelectTrigger id="vlm-provider" className="w-full">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="medGemma">MedGemma</SelectItem>
                      <SelectItem value="gemini">Gemini</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="claude">Claude</SelectItem>
                      <SelectItem value="kimi">Kimi (HF)</SelectItem>
                      <SelectItem value="qwen">Qwen (HF)</SelectItem>
                      <SelectItem value="gemma">Gemma 4 (HF)</SelectItem>
                      <SelectItem value="vllm">vLLM (OpenAI API)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="medgemma-instruction" className="text-sm font-semibold">Instruction (Optional)</Label>
                  <textarea
                    id="medgemma-instruction"
                    value={medgemmaInstruction}
                    onChange={(e) => {
                      const value = e.target.value;
                      setMedgemmaInstruction(value);
                      toolboxState.setMedgemmaInstruction(value);
                    }}
                    placeholder="Enter instruction (e.g., 'You are an instructor teaching medical students...')"
                    className="min-h-[60px] text-sm bg-primary-dark border border-primary-main rounded p-2 text-white placeholder:text-primary-light resize-y"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="medgemma-query" className="text-sm font-semibold">Query</Label>
                  <textarea
                    id="medgemma-query"
                    value={medgemmaQuery}
                    onChange={(e) => {
                      const value = e.target.value;
                      setMedgemmaQuery(value);
                      toolboxState.setMedgemmaQuery(value);
                    }}
                    placeholder="Enter your query/question"
                    className="min-h-[60px] text-sm bg-primary-dark border border-primary-main rounded p-2 text-white placeholder:text-primary-light resize-y"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label className="text-sm font-semibold">Slice Range (Optional)</Label>
                  <div className="flex gap-2">
                    <div className="flex flex-col gap-1 flex-1">
                      <Label htmlFor="medgemma-start-slice" className="text-xs text-primary-light">Start Slice (min: 1)</Label>
                      <input
                        id="medgemma-start-slice"
                        type="number"
                        min="1"
                        value={medgemmaStartSlice ?? ''}
                        onChange={(e) => {
                          const value = e.target.value === '' ? null : parseInt(e.target.value, 10);
                          setMedgemmaStartSlice(value);
                          toolboxState.setMedgemmaStartSlice(value);
                        }}
                        placeholder="1"
                        className="text-sm bg-primary-dark border border-primary-main rounded p-2 text-white placeholder:text-primary-light"
                      />
                    </div>
                    <div className="flex flex-col gap-1 flex-1">
                      <Label htmlFor="medgemma-end-slice" className="text-xs text-primary-light">End Slice (max: total slices)</Label>
                      <input
                        id="medgemma-end-slice"
                        type="number"
                        min="1"
                        value={medgemmaEndSlice ?? ''}
                        onChange={(e) => {
                          const value = e.target.value === '' ? null : parseInt(e.target.value, 10);
                          setMedgemmaEndSlice(value);
                          toolboxState.setMedgemmaEndSlice(value);
                        }}
                        placeholder="Total slices"
                        className="text-sm bg-primary-dark border border-primary-main rounded p-2 text-white placeholder:text-primary-light"
                      />
                    </div>
                  </div>
                </div>
                {vlmProvider === 'medGemma' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="medgemma-variant" className="text-sm font-semibold">
                        MedGemma model
                      </Label>
                      <Select
                        value={medgemmaVariant}
                        onValueChange={value => {
                          const v = value as MedgemmaVariantId;
                          setMedgemmaVariant(v);
                          toolboxState.setMedgemmaVariant(v);
                        }}
                      >
                        <SelectTrigger id="medgemma-variant" className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1.5-4b">1.5-4B</SelectItem>
                          <SelectItem value="27b">1-27b</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex justify-between items-center gap-4 py-1">
                      <Label htmlFor="medgemma-thinking" className="text-sm font-semibold">
                        Thinking
                      </Label>
                      <Switch
                        id="medgemma-thinking"
                        checked={medgemmaThinkingEnabled}
                        onCheckedChange={checked => {
                          setMedgemmaThinkingEnabled(checked);
                          toolboxState.setMedgemmaThinkingEnabled(checked);
                        }}
                      />
                    </div>
                  </>
                )}
                {vlmProvider === 'gemini' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="gemini-model" className="text-sm font-semibold">
                        Gemini model id (API)
                      </Label>
                      <Input
                        id="gemini-model"
                        type="text"
                        value={geminiModel}
                        onChange={e => {
                          const v = e.target.value;
                          setGeminiModel(v);
                          toolboxState.setGeminiModel(v);
                        }}
                        placeholder="e.g. gemini-3-flash-preview"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="gemini-thinking-level" className="text-sm font-semibold">
                        Thinking level (reasoning)
                      </Label>
                      <Select
                        value={geminiThinkingLevel || 'default'}
                        onValueChange={value => {
                          const level =
                            value === 'default' ? '' : (value as 'low' | 'medium' | 'high');
                          setGeminiThinkingLevel(level);
                          toolboxState.setGeminiThinkingLevel(level);
                        }}
                      >
                        <SelectTrigger id="gemini-thinking-level" className="w-full">
                          <SelectValue placeholder="Default" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="default">Default (omit)</SelectItem>
                          <SelectItem value="low">low</SelectItem>
                          <SelectItem value="medium">medium</SelectItem>
                          <SelectItem value="high">high</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </>
                )}
                {vlmProvider === 'openai' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="openai-model" className="text-sm font-semibold">
                        OpenAI model id (API)
                      </Label>
                      <Input
                        id="openai-model"
                        type="text"
                        value={openaiModel}
                        onChange={e => {
                          const v = e.target.value;
                          setOpenaiModel(v);
                          toolboxState.setOpenaiModel(v);
                        }}
                        placeholder="e.g. gpt-5.4"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="openai-reasoning-effort" className="text-sm font-semibold">
                        Reasoning effort
                      </Label>
                      <Input
                        id="openai-reasoning-effort"
                        type="text"
                        value={openaiReasoningEffort}
                        onChange={e => {
                          const v = e.target.value;
                          setOpenaiReasoningEffort(v);
                          toolboxState.setOpenaiReasoningEffort(v);
                        }}
                        placeholder="none, low, medium, high (model-dependent)"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                  </>
                )}
                {vlmProvider === 'claude' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="claude-model" className="text-sm font-semibold">
                        Claude model id (API)
                      </Label>
                      <Input
                        id="claude-model"
                        type="text"
                        value={claudeModel}
                        onChange={e => {
                          const v = e.target.value;
                          setClaudeModel(v);
                          toolboxState.setClaudeModel(v);
                        }}
                        placeholder="e.g. claude-sonnet-4-20250514"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="claude-thinking-effort" className="text-sm font-semibold">
                        Thinking effort (adaptive)
                      </Label>
                      <Select
                        value={claudeThinkingEffort || 'default'}
                        onValueChange={value => {
                          const level =
                            value === 'default'
                              ? ''
                              : (value as 'low' | 'medium' | 'high' | 'max');
                          setClaudeThinkingEffort(level);
                          toolboxState.setClaudeThinkingEffort(level);
                        }}
                      >
                        <SelectTrigger id="claude-thinking-effort" className="w-full">
                          <SelectValue placeholder="Default" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="default">Default (omit)</SelectItem>
                          <SelectItem value="low">low</SelectItem>
                          <SelectItem value="medium">medium</SelectItem>
                          <SelectItem value="high">high</SelectItem>
                          <SelectItem value="max">max</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </>
                )}
                {vlmProvider === 'kimi' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="kimi-model" className="text-sm font-semibold">
                        Kimi model id (HF)
                      </Label>
                      <Input
                        id="kimi-model"
                        type="text"
                        value={kimiModel}
                        onChange={e => {
                          const v = e.target.value;
                          setKimiModel(v);
                          toolboxState.setKimiModel(v);
                        }}
                        placeholder="e.g. moonshotai/Kimi-K2.5:novita"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex justify-between items-center gap-4 py-1">
                      <Label htmlFor="kimi-reasoning" className="text-sm font-semibold">
                        Thinking
                      </Label>
                      <Switch
                        id="kimi-reasoning"
                        checked={kimiReasoningEnabled}
                        onCheckedChange={checked => {
                          setKimiReasoningEnabled(checked);
                          toolboxState.setKimiReasoningEnabled(checked);
                        }}
                      />
                    </div>
                  </>
                )}
                {vlmProvider === 'qwen' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="qwen-model" className="text-sm font-semibold">
                        Qwen model id (HF)
                      </Label>
                      <Input
                        id="qwen-model"
                        type="text"
                        value={qwenModel}
                        onChange={e => {
                          const v = e.target.value;
                          setQwenModel(v);
                          toolboxState.setQwenModel(v);
                        }}
                        placeholder="e.g. Qwen/Qwen3.5-397B-A17B:novita"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex justify-between items-center gap-4 py-1">
                      <Label htmlFor="qwen-thinking" className="text-sm font-semibold">
                        Thinking
                      </Label>
                      <Switch
                        id="qwen-thinking"
                        checked={qwenThinkingEnabled}
                        onCheckedChange={checked => {
                          setQwenThinkingEnabled(checked);
                          toolboxState.setQwenThinkingEnabled(checked);
                        }}
                      />
                    </div>
                  </>
                )}
                {vlmProvider === 'gemma' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="gemma-model" className="text-sm font-semibold">
                        Gemma model id (HF)
                      </Label>
                      <Input
                        id="gemma-model"
                        type="text"
                        value={gemmaModel}
                        onChange={e => {
                          const v = e.target.value;
                          setGemmaModel(v);
                          toolboxState.setGemmaModel(v);
                        }}
                        placeholder="e.g. google/gemma-4-31B-it:novita"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex justify-between items-center gap-4 py-1">
                      <Label htmlFor="gemma-thinking" className="text-sm font-semibold">
                        Thinking
                      </Label>
                      <Switch
                        id="gemma-thinking"
                        checked={gemmaThinkingEnabled}
                        onCheckedChange={checked => {
                          setGemmaThinkingEnabled(checked);
                          toolboxState.setGemmaThinkingEnabled(checked);
                        }}
                      />
                    </div>
                  </>
                )}
                {vlmProvider === 'vllm' && (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="vllm-base-url" className="text-sm font-semibold">
                        vLLM base URL (OpenAI-compatible, include /v1)
                      </Label>
                      <Input
                        id="vllm-base-url"
                        type="text"
                        value={vllmBaseUrl}
                        onChange={e => {
                          const v = e.target.value;
                          setVllmBaseUrl(v);
                          toolboxState.setVllmBaseUrl(v);
                        }}
                        placeholder="http://host.docker.internal:8000/v1"
                        className="text-sm bg-primary-dark border border-primary-main text-white"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="vllm-family" className="text-sm font-semibold">
                        Model family (optional)
                      </Label>
                      <Select
                        value={vllmFamily || 'auto'}
                        onValueChange={value => {
                          const fam = value === 'auto' ? '' : (value as VllmFamilyId);
                          setVllmFamily(fam);
                          toolboxState.setVllmFamily(fam);
                        }}
                      >
                        <SelectTrigger id="vllm-family" className="w-full">
                          <SelectValue placeholder="Auto from model id" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Auto (from first model id)</SelectItem>
                          <SelectItem value="internvl">InternVL</SelectItem>
                          <SelectItem value="qwen">Qwen</SelectItem>
                          <SelectItem value="kimi">Kimi</SelectItem>
                          <SelectItem value="gemma">Gemma</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="vllm-thinking-level" className="text-sm font-semibold">
                        Thinking
                      </Label>
                      <Select
                        value={vllmThinkingLevel}
                        onValueChange={value => {
                          const level = value as VllmThinkingLevel;
                          setVllmThinkingLevel(level);
                          toolboxState.setVllmThinkingLevel(level);
                        }}
                      >
                        <SelectTrigger id="vllm-thinking-level" className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="off">Off</SelectItem>
                          <SelectItem value="on">On</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </>
                )}
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => {
                    commandsManager?.run('testVlm', {
                      vlmProvider,
                      instruction: medgemmaInstruction,
                      query: medgemmaQuery,
                      startSlice: medgemmaStartSlice,
                      endSlice: medgemmaEndSlice,
                      medgemmaVariant,
                      medgemmaThinkingEnabled,
                      geminiModel: geminiModel?.trim() || undefined,
                      geminiThinkingLevel,
                      openaiModel: openaiModel?.trim() || undefined,
                      openaiReasoningEffort: openaiReasoningEffort?.trim() || undefined,
                      claudeModel: claudeModel?.trim() || undefined,
                      claudeThinkingEffort,
                      kimiModel: kimiModel?.trim() || undefined,
                      kimiReasoningEnabled,
                      qwenModel: qwenModel?.trim() || undefined,
                      qwenThinkingEnabled,
                      gemmaModel: gemmaModel?.trim() || undefined,
                      gemmaThinkingEnabled,
                      vllmBaseUrl: vllmBaseUrl?.trim() || undefined,
                      vllmFamily,
                      vllmThinkingLevel,
                    });
                  }}
                  disabled={!medgemmaQuery || medgemmaQuery.trim() === ''}
                  className="w-full"
                >
                  Run
                </Button>
                {medgemmaResult && (
                  <div className="flex flex-col gap-2 mt-2">
                    <Label className="text-sm font-semibold">Result:</Label>
                    <div className="bg-primary-dark border border-primary-main rounded p-3 max-h-[300px] overflow-y-auto">
                      <pre className="whitespace-pre-wrap break-words text-sm text-white">
                        {medgemmaResult}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            )}
            </React.Fragment>
          );
        })}
        {activeToolOptions && (
          <div className="bg-primary-dark mt-1 h-auto px-2">
            <ToolSettings options={activeToolOptions} />
          </div>
        )}
      </PanelSection.Content>
      )}
    </PanelSection>
  );
}
