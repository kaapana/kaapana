import React, { useEffect, useRef, useState } from 'react';
import { Icons, Label, PanelSection, Switch, Button, ToggleGroup, ToggleGroupItem } from '@ohif/ui-next';
import { Brush, Lock, LockOpen } from 'lucide-react';
import { useSystem, useToolbar } from '@ohif/core';
import classnames from 'classnames';
import { useTranslation } from 'react-i18next';
import * as promptModel from '../model/promptModel';
import { toolboxState } from '../utils/toolboxState';

interface ButtonProps {
  isActive?: boolean;
  options?: unknown;
}

const BRUSH_SIZE_MIN = 1;
const BRUSH_SIZE_MAX = 60;
const BRUSH_SIZE_STEP = 1;

function ShortcutKey({
  keys,
  title,
  className,
}: {
  keys: string;
  title: string;
  className?: string;
}) {
  return (
    <kbd
      title={`${title} (${keys})`}
      aria-label={`${title}: ${keys}`}
      className={classnames(
        'border-primary/30 bg-background text-muted-foreground inline-flex h-5 min-w-5 items-center justify-center rounded border px-1 text-[10px] font-semibold leading-none',
        className
      )}
    >
      {keys}
    </kbd>
  );
}

function ShortcutHint({ keys, label, title }: { keys: string; label: string; title: string }) {
  return (
    <span
      title={`${title} (${keys})`}
      className="border-primary/20 text-muted-foreground inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px]"
    >
      <ShortcutKey
        keys={keys}
        title={title}
        className="border-transparent bg-transparent p-0 text-[11px]"
      />
      <span>{label}</span>
    </span>
  );
}

export default function NnInteractivePanel({
  buttonSectionId,
  title,
  defaultOpen = true,
}: {
  buttonSectionId: string;
  title: string;
  defaultOpen?: boolean;
}) {
  const { servicesManager, commandsManager } = useSystem();
  const { t } = useTranslation();

  const {
    toolbarService,
    customizationService,
    segmentationService,
    viewportGridService,
    measurementService,
    displaySetService,
    uiNotificationService,
  } = servicesManager.services;

  const onInteractionRef = useRef<((args: { itemId: string }) => void) | null>(null);
  const isAIToolBox = buttonSectionId === 'aiToolBox';
  const [showConfig, setShowConfig] = useState(false);
  const [isLocked, setIsLocked] = useState(toolboxState.getLocked());
  const [liveMode, setLiveMode] = useState(toolboxState.getLiveMode());
  const [posNeg, setPosNeg] = useState(toolboxState.getPosNeg());
  const [sessionActive, setSessionActive] = useState(toolboxState.getSessionActive());
  const [initializing, setInitializing] = useState(false);
  const [nnInteractiveAvailable, setNnInteractiveAvailable] = useState<boolean | null>(null);
  const [showManualControl, setShowManualControl] = useState(false);
  const [brushSize, setBrushSize] = useState(12);
  const lastSeriesRef = useRef<string>('');
  const hotkeysDisabled = isAIToolBox && isLocked;

  const getActiveSeriesUID = (): string => {
    try {
      const { activeViewportId, viewports } = viewportGridService.getState();
      const dsUID = viewports.get(activeViewportId)?.displaySetInstanceUIDs?.[0];
      const ds = displaySetService.activeDisplaySets.find(
        (d: any) => d.displaySetInstanceUID === dsUID
      );
      return ds?.SeriesInstanceUID ?? '';
    } catch {
      return '';
    }
  };

  useEffect(() => {
    const updateLocalState = () => {
      setLiveMode(toolboxState.getLiveMode());
      setPosNeg(toolboxState.getPosNeg());
      setIsLocked(toolboxState.getLocked());

      if (isAIToolBox) {
        const series = getActiveSeriesUID();
        if (series && lastSeriesRef.current && series !== lastSeriesRef.current) {
          toolboxState.setSessionActive(false);
        }
        if (series) {
          lastSeriesRef.current = series;
        }
        setSessionActive(toolboxState.getSessionActive());
      }
    };

    updateLocalState();
    const interval = setInterval(updateLocalState, 100);

    return () => {
      clearInterval(interval);
      toolboxState.setManualCorrectionMode(false);
      toolboxState.setPosNeg(false);
    };
  }, []);

  useEffect(() => {
    if (!isAIToolBox || hotkeysDisabled) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isInputField =
        activeElement?.tagName === 'INPUT' ||
        activeElement?.tagName === 'TEXTAREA' ||
        (activeElement as HTMLElement)?.contentEditable === 'true';

      if (isInputField) {
        return;
      }

      switch (event.key.toLowerCase()) {
        case 'q': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const newLiveMode = !toolboxState.getLiveMode();
          setLiveMode(newLiveMode);
          toolboxState.setLiveMode(newLiveMode);
          break;
        }
        case 't': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const newPosNeg = !toolboxState.getPosNeg();
          setPosNeg(newPosNeg);
          toolboxState.setPosNeg(newPosNeg);
          break;
        }
        case 'p':
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          toolboxState.setManualCorrectionMode(false);
          onInteractionRef.current?.({ itemId: 'Probe2' });
          break;
        case 'b':
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          toolboxState.setManualCorrectionMode(false);
          onInteractionRef.current?.({ itemId: 'RectangleROI2' });
          break;
        case 's':
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          toolboxState.setManualCorrectionMode(false);
          onInteractionRef.current?.({ itemId: 'PlanarFreehandROI2' });
          break;
        case 'l':
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          toolboxState.setManualCorrectionMode(false);
          onInteractionRef.current?.({ itemId: 'PlanarFreehandROI3' });
          break;
        case 'n': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          commandsManager.run('armNextNninterObject');
          break;
        }
        case 'c': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          setManualCorrectionBrush();
          break;
        }
        case '+':
        case '=': {
          if (!nnInteractiveAvailable || event.ctrlKey || event.metaKey) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          adjustBrushSize(BRUSH_SIZE_STEP);
          break;
        }
        case '-':
        case '_': {
          if (!nnInteractiveAvailable || event.ctrlKey || event.metaKey) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          adjustBrushSize(-BRUSH_SIZE_STEP);
          break;
        }
        case 'r': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const { activeViewportId: avId } = viewportGridService.getState();
          const activeSeg = segmentationService.getActiveSegmentation(avId);
          const activeSegment = segmentationService.getActiveSegment(avId);
          if (activeSeg?.segmentationId && activeSegment?.segmentIndex != null) {
            commandsManager.run('resetSegment', {
              segmentationId: activeSeg.segmentationId,
              segmentIndex: activeSegment.segmentIndex,
            });
          }
          break;
        }
        case 'o': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const next = !toolboxState.getPromptsVisible();
          toolboxState.setPromptsVisible(next);
          // Prompts are Cornerstone annotations (not measurements) — toggle them directly.
          promptModel.setPromptsVisible(next);
          break;
        }
        case 'z': {
          if (!nnInteractiveAvailable) {
            return;
          }
          if (event.ctrlKey && !event.shiftKey) {
            event.preventDefault();
            event.stopPropagation();
            commandsManager.run('undoNninter');
          }
          break;
        }
        case 'delete': {
          if (!nnInteractiveAvailable) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          handleDeleteObject();
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [brushSize, hotkeysDisabled, isAIToolBox, nnInteractiveAvailable, sessionActive]);

  useEffect(() => {
    if (!isLocked) {
      return;
    }

    try {
      if (liveMode) {
        setLiveMode(false);
        toolboxState.setLiveMode(false);
      }
      commandsManager?.run?.('setToolActive', { toolName: 'Pan' });
    } catch {
      // no-op
    }
  }, [isLocked]);

  useEffect(() => {
    if (!isAIToolBox) {
      return;
    }

    let mounted = true;
    const checkAvailability = async () => {
      try {
        const response = await fetch('/nninteractive/infer/availability', {
          cache: 'no-store',
          headers: { accept: 'application/json' },
        });
        if (!mounted) {
          return;
        }
        if (!response.ok) {
          setNnInteractiveAvailable(false);
          toolboxState.setSessionActive(false);
          return;
        }
        const data = await response.json();
        const available = !!data?.available;
        setNnInteractiveAvailable(available);
        if (!available) {
          toolboxState.setSessionActive(false);
        }
      } catch {
        if (mounted) {
          setNnInteractiveAvailable(false);
          toolboxState.setSessionActive(false);
        }
      }
    };

    checkAvailability();
    const interval = setInterval(checkAvailability, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [isAIToolBox]);

  useEffect(() => {
    if (!isAIToolBox || !nnInteractiveAvailable) {
      return;
    }

    const poll = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        return;
      }
      commandsManager.run('nninterSessionStatus');
    };

    const interval = setInterval(poll, 20000);
    const onPageHide = () => {
      if (toolboxState.getSessionActive()) {
        commandsManager.run('closeNninterSession');
      }
    };

    window.addEventListener('pagehide', onPageHide);
    return () => {
      clearInterval(interval);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [isAIToolBox, nnInteractiveAvailable]);

  const { toolbarButtons: toolboxSections, onInteraction } = useToolbar({
    servicesManager,
    buttonSection: buttonSectionId,
  });
  onInteractionRef.current = onInteraction;

  if (!toolboxSections.length) {
    return null;
  }

  if (!toolboxSections.every(section => section.componentProps.buttonSection)) {
    throw new Error(
      'Toolbox accepts only button sections at the top level, not buttons. Create at least one button section.'
    );
  }

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

  toolboxSections.reduce((activeOptions, section) => {
    if (activeOptions) {
      return activeOptions;
    }
    const sectionId = section.componentProps.buttonSection;
    const buttons = toolbarService.getButtonSection(sectionId);
    return findActiveOptions(buttons);
  }, null);

  const handleInteraction = ({ itemId }: { itemId: string }) => {
    if (isAIToolBox && isLocked && itemId !== 'Pan') {
      commandsManager?.run?.('setToolActive', { toolName: 'Pan' });
      return;
    }
    if (isAIToolBox && !nnInteractiveAvailable && itemId !== 'Pan') {
      return;
    }
    if (isAIToolBox && !sessionActive && itemId !== 'Pan') {
      uiNotificationService?.show?.({
        title: 'nnInteractive',
        message: 'Click Initialize to start a session first.',
        type: 'info',
      });
      return;
    }
    if (isAIToolBox && promptToolIds.includes(itemId)) {
      toolboxState.setManualCorrectionMode(false);
    }
    onInteraction?.({ itemId });
  };

  const promptToolIds = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'];

  const aiActiveSegmentation = () => {
    const { activeViewportId: avId } = viewportGridService.getState();
    return (
      segmentationService.getActiveSegmentation(avId) ??
      segmentationService.getSegmentations()?.[0]
    );
  };

  const handleInitialize = async () => {
    if (!nnInteractiveAvailable || initializing || sessionActive) {
      return;
    }
    // Block the button while the backend session is being created so a slow
    // init can't be spammed. The finally re-enables it if anything goes wrong;
    // on success sessionActive keeps it disabled ("Session ready").
    setInitializing(true);
    try {
      await commandsManager.run('initNninter');
    } catch (error) {
      console.error('initNninter failed:', error);
    } finally {
      setInitializing(false);
    }
  };
  const handleRun = () => {
    if (nnInteractiveAvailable) {
      commandsManager.run('nninter');
    }
  };
  const handleUndo = () => {
    if (nnInteractiveAvailable) {
      commandsManager.run('undoNninter');
    }
  };

  const handleResetObject = () => {
    const { activeViewportId: avId } = viewportGridService.getState();
    if (!nnInteractiveAvailable) {
      return;
    }
    const seg = segmentationService.getActiveSegmentation(avId);
    const segment = segmentationService.getActiveSegment(avId);
    if (seg?.segmentationId && segment?.segmentIndex != null) {
      commandsManager.run('resetSegment', {
        segmentationId: seg.segmentationId,
        segmentIndex: segment.segmentIndex,
      });
    }
  };

  const handleNextObject = () => {
    if (!nnInteractiveAvailable) {
      return;
    }

    commandsManager.run('armNextNninterObject');
  };

  const handleDeleteObject = () => {
    if (!nnInteractiveAvailable) {
      return;
    }

    const { activeViewportId: avId } = viewportGridService.getState();
    const activeSeg = segmentationService.getActiveSegmentation(avId);
    const activeSegment = segmentationService.getActiveSegment(avId);
    if (activeSeg?.segmentationId && activeSegment?.segmentIndex != null) {
      const { segmentationId } = activeSeg;
      const { segmentIndex } = activeSegment;
      // deleteSegment clears the object's prompt annotations and resets the backend.
      commandsManager.run('deleteSegment', { segmentationId, segmentIndex });
    }
  };

  const handleExport = () => {
    const seg = aiActiveSegmentation();
    if (!nnInteractiveAvailable) {
      return;
    }
    if (seg?.segmentationId) {
      commandsManager.run({
        commandName: 'storeNninterSegmentation',
        commandOptions: { segmentationId: seg.segmentationId },
        context: 'SEGMENTATION',
      });
    }
  };

  const hasActiveAiSegment = () => {
    const { activeViewportId: avId } = viewportGridService.getState();
    const seg = segmentationService.getActiveSegmentation(avId);
    const segment = segmentationService.getActiveSegment(avId);
    return !!seg?.segmentationId && segment?.segmentIndex != null;
  };

  const applyBrushSize = (nextSize: number) => {
    const clampedSize = Math.min(BRUSH_SIZE_MAX, Math.max(BRUSH_SIZE_MIN, nextSize));
    setBrushSize(clampedSize);
    commandsManager.run('setBrushSize', {
      value: clampedSize,
      toolNames: ['CircularBrush', 'CircularEraser'],
    });
  };

  const adjustBrushSize = (delta: number) => {
    if (!nnInteractiveReady || !sessionActive || !hasActiveAiSegment()) {
      return;
    }

    applyBrushSize(brushSize + delta);
  };

  const setManualCorrectionBrush = () => {
    if (!nnInteractiveReady || !sessionActive || !hasActiveAiSegment()) {
      uiNotificationService?.show?.({
        title: 'Manual correction',
        message: 'Select an active nnInteractive segment first.',
        type: 'info',
      });
      return;
    }

    toolboxState.setManualCorrectionMode(true);
    applyBrushSize(brushSize);
    commandsManager.run('setToolActiveToolbar', {
      toolName: toolboxState.getPosNeg() ? 'CircularEraser' : 'CircularBrush',
    });
  };

  const handleBrushSizeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    applyBrushSize(Number(event.target.value));
  };

  const CustomConfigComponent = customizationService.getCustomization(`${buttonSectionId}.config`);
  const nnInteractiveReady = nnInteractiveAvailable === true;
  const nnInteractiveChecking = nnInteractiveAvailable === null;
  const shouldCollapse = isAIToolBox && isLocked;

  const renderGenericToolbox = () =>
    toolboxSections.map(section => {
      const sectionId = section.componentProps.buttonSection;
      const buttons = toolbarService.getButtonSection(sectionId) as any[];

      return (
        <div key={sectionId} className="bg-muted flex flex-wrap space-x-2 py-2 px-1">
          {buttons.map(tool => {
            if (!tool) {
              return null;
            }
            const { id, Component, componentProps } = tool;

            return (
              <div key={id} className={classnames('ml-1')}>
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
      );
    });

  return (
    <PanelSection
      key={isAIToolBox ? `toolbox-${isLocked}` : buttonSectionId}
      defaultOpen={defaultOpen && !shouldCollapse}
    >
      <PanelSection.Header className="flex items-center justify-between">
        <span
          className={classnames('flex items-center gap-2', {
            'pointer-events-none': shouldCollapse,
          })}
        >
          <span className="pointer-events-auto">{t(title)}</span>
          {isAIToolBox && (
            <button
              type="button"
              className={classnames(
                'ml-auto h-5 w-5 text-primary hover:opacity-80 pointer-events-auto cursor-pointer'
              )}
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

          {!isAIToolBox && renderGenericToolbox()}

          {isAIToolBox &&
            toolboxSections.map(section => {
              const sectionId = section.componentProps.buttonSection;
              const buttons = toolbarService.getButtonSection(sectionId) as any[];

              return (
                <div key={sectionId} className="flex flex-col gap-3 py-2 px-2">
                  <div className="text-muted-foreground text-sm">Model: nnInteractive</div>
                  {!nnInteractiveReady && (
                    <div className="text-muted-foreground rounded border border-primary/20 p-2 text-xs">
                      {nnInteractiveChecking
                        ? 'Checking nnInteractive availability...'
                        : 'nnInteractive is not installed or the backend is unavailable.'}
                    </div>
                  )}

                  <Button
                    variant="default"
                    size="sm"
                    className="w-full"
                    disabled={!nnInteractiveReady || sessionActive || initializing}
                    onClick={handleInitialize}
                  >
                    {sessionActive ? 'Session ready' : initializing ? 'Initializing...' : 'Initialize'}
                  </Button>
                  <div
                    className={classnames(
                      'text-xs',
                      sessionActive ? 'text-green-500' : 'text-muted-foreground'
                    )}
                  >
                    {sessionActive
                      ? 'Session ready'
                      : initializing
                        ? 'Initializing session...'
                        : nnInteractiveReady
                          ? 'Initialize to start a session'
                          : 'Optional nnInteractive backend unavailable'}
                  </div>

                  <div className="border-t border-primary/20" />

                  <div className="flex flex-col gap-1">
                    <div className="flex items-center justify-between gap-2">
                      <Label>Prompt Type</Label>
                      <ShortcutKey
                        keys="T"
                        title="Toggle positive or negative prompt"
                      />
                    </div>
                    <ToggleGroup
                      type="single"
                      size="sm"
                      className="w-full"
                      value={posNeg ? 'negative' : 'positive'}
                      disabled={!nnInteractiveReady || !sessionActive}
                      onValueChange={value => {
                        if (!value) {
                          return;
                        }
                        const neg = value === 'negative';
                        setPosNeg(neg);
                        toolboxState.setPosNeg(neg);
                        if (toolboxState.getManualCorrectionMode() && sessionActive) {
                          commandsManager.run('setToolActiveToolbar', {
                            toolName: neg ? 'CircularEraser' : 'CircularBrush',
                          });
                        }
                      }}
                    >
                      <ToggleGroupItem value="positive" className="flex-1">
                        positive
                      </ToggleGroupItem>
                      <ToggleGroupItem value="negative" className="flex-1">
                        negative
                      </ToggleGroupItem>
                    </ToggleGroup>
                  </div>

                  <div className="flex flex-col gap-1">
                    <Label>Interaction Tools</Label>
                    <div
                      className={classnames('flex flex-wrap gap-1', {
                        'opacity-40 pointer-events-none': !nnInteractiveReady || !sessionActive,
                      })}
                    >
                      {buttons
                        .filter(tool => tool && promptToolIds.includes(tool.id))
                        .map(tool => {
                          const { id, Component, componentProps } = tool;
                          return (
                            <div key={id} className="ml-1">
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
                    <div className="flex flex-wrap gap-1 pt-1">
                      <ShortcutHint keys="P" label="Point" title="Activate point prompt" />
                      <ShortcutHint keys="B" label="BBox" title="Activate bounding box prompt" />
                      <ShortcutHint keys="S" label="Scribble" title="Activate scribble prompt" />
                      <ShortcutHint keys="L" label="Lasso" title="Activate lasso prompt" />
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-1.5"
                      disabled={!nnInteractiveReady || !sessionActive}
                      onClick={handleUndo}
                    >
                      Undo
                      <ShortcutKey keys="Ctrl+Z" title="Undo last nnInteractive prompt" />
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-1.5"
                      disabled={!nnInteractiveReady || !sessionActive}
                      onClick={handleResetObject}
                    >
                      Reset Object
                      <ShortcutKey keys="R" title="Reset current object" />
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-1.5"
                      disabled={!nnInteractiveReady || !sessionActive}
                      onClick={handleNextObject}
                    >
                      Next Object
                      <ShortcutKey keys="N" title="Move to next object" />
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-1.5"
                      disabled={!nnInteractiveReady || !sessionActive || !hasActiveAiSegment()}
                      onClick={handleDeleteObject}
                    >
                      Delete Object
                      <ShortcutKey keys="Delete" title="Delete current object" />
                    </Button>
                  </div>

                  <div className="flex flex-col gap-1">
                    <button
                      type="button"
                      className="flex items-center gap-1 text-sm text-primary hover:opacity-80"
                      onClick={() => setShowManualControl(v => !v)}
                    >
                      <span>{showManualControl ? 'v' : '>'}</span>
                      <span>Manual Control</span>
                    </button>
                    {showManualControl && (
                      <div className="flex flex-col gap-2 pl-3">
                        <div className="flex items-center justify-between gap-2">
                          <Label htmlFor="auto-run" className="flex items-center gap-1.5">
                            Auto Run Prediction
                            <ShortcutKey keys="Q" title="Toggle auto-run prediction" />
                          </Label>
                          <Switch
                            id="auto-run"
                            checked={liveMode}
                            disabled={!nnInteractiveReady || !sessionActive}
                            onCheckedChange={checked => {
                              setLiveMode(checked);
                              toolboxState.setLiveMode(checked);
                            }}
                          />
                        </div>
                        <Button variant="secondary" size="sm" disabled={!nnInteractiveReady || !sessionActive} onClick={handleRun}>
                          Run
                        </Button>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-primary/20" />

                  <div className="flex flex-col gap-2">
                    <div className="text-muted-foreground text-sm">Manual Correction</div>
                    <Button
                      variant="default"
                      size="sm"
                      className="relative w-full justify-center gap-2"
                      disabled={!nnInteractiveReady || !sessionActive || !hasActiveAiSegment()}
                      onClick={setManualCorrectionBrush}
                    >
                      <span className="flex items-center gap-1">
                        <Brush className="h-4 w-4" />
                        Brush
                      </span>
                      <ShortcutKey
                        keys="C"
                        title="Activate manual correction brush"
                        className="absolute right-2"
                      />
                    </Button>
                    <div
                      className={classnames('flex flex-col gap-1', {
                        'opacity-40 pointer-events-none':
                          !nnInteractiveReady || !sessionActive || !hasActiveAiSegment(),
                      })}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <Label htmlFor="nninter-brush-size">Brush size</Label>
                        <div className="flex items-center gap-1">
                          <ShortcutKey keys="-" title="Make brush smaller" />
                          <ShortcutKey keys="+" title="Make brush bigger" />
                          <span className="text-muted-foreground text-xs">{brushSize}px</span>
                        </div>
                      </div>
                      <input
                        id="nninter-brush-size"
                        type="range"
                        min={BRUSH_SIZE_MIN}
                        max={BRUSH_SIZE_MAX}
                        step={BRUSH_SIZE_STEP}
                        value={brushSize}
                        onChange={handleBrushSizeChange}
                      />
                    </div>
                  </div>

                  <div className="border-t border-primary/20" />

                  <Button
                    variant="default"
                    size="sm"
                    className="w-full"
                    disabled={!nnInteractiveReady || !sessionActive}
                    onClick={handleExport}
                  >
                    Export DICOM SEG
                  </Button>
                </div>
              );
            })}
        </PanelSection.Content>
      )}
    </PanelSection>
  );
}
