import React, { useEffect, useState } from 'react';
import {
  Button,
  Icons,
  Label,
  PanelSection,
  Switch,
  ToggleGroup,
  ToggleGroupItem,
} from '@ohif/ui-next';
import { useSystem } from '@ohif/core';
import { Brush } from 'lucide-react';
import classnames from 'classnames';

import {
  ToolNnInteractiveBbox,
  ToolNnInteractiveLasso,
  ToolNnInteractivePoint,
  ToolNnInteractiveScribble,
} from '../icons/PromptIcons';
import * as objectModel from '../model/objectModel';
import * as promptModel from '../model/promptModel';
import { isAvailable } from '../model/serverApi';
import { sessionState } from '../model/sessionModel';
import { toolboxState } from '../utils/toolboxState';
import { ObjectList, ObjectRow, setObjectVisible, useObjects } from './ObjectList';

const BRUSH_SIZE_MIN = 1;
const BRUSH_SIZE_MAX = 60;
const BRUSH_TOOLS = ['CircularBrush', 'CircularEraser'];

const PROMPT_TOOLS = [
  { toolName: 'Probe2', label: 'Point', key: 'P', Icon: ToolNnInteractivePoint },
  { toolName: 'RectangleROI2', label: 'Box', key: 'B', Icon: ToolNnInteractiveBbox },
  { toolName: 'PlanarFreehandROI2', label: 'Scribble', key: 'S', Icon: ToolNnInteractiveScribble },
  { toolName: 'PlanarFreehandROI3', label: 'Lasso', key: 'L', Icon: ToolNnInteractiveLasso },
];

function Key({ children }: { children: React.ReactNode }) {
  return (
    <kbd
      className="text-muted-foreground border-primary/30 rounded border"
      style={{ fontSize: 10, lineHeight: '14px', padding: '0 4px', fontFamily: 'inherit' }}
    >
      {children}
    </kbd>
  );
}

function SectionLabel({ children, hint }: { children: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <Label>{children}</Label>
      {hint}
    </div>
  );
}

type Status = 'checking' | 'unavailable' | 'idle' | 'starting' | 'ready' | 'error';

const STATUS_TEXT: Record<Status, { text: string; color: string; hint?: string }> = {
  checking: { text: 'Checking…', color: '#9ca3af' },
  unavailable: {
    text: 'Unavailable',
    color: '#ef4444',
    hint: 'The nnInteractive backend is not installed or not reachable.',
  },
  idle: { text: 'Idle', color: '#9ca3af', hint: 'A session starts with your first prompt.' },
  starting: { text: 'Starting…', color: '#f59e0b' },
  ready: { text: 'Ready', color: '#22c55e' },
  error: { text: 'Error', color: '#ef4444' },
};

/**
 * The nnInteractive workflow in one panel, top to bottom: prompt type → tool → objects → save.
 * Every action has exactly one control here; its shortcut is printed on that control.
 */
export default function NnInteractivePanel() {
  const { servicesManager, commandsManager } = useSystem();
  const { viewportGridService, toolGroupService, uiNotificationService } = servicesManager.services;

  const [available, setAvailable] = useState<boolean | null>(null);
  const [session, setSession] = useState(sessionState.get());
  const [ui, setUi] = useState(toolboxState.get());
  const [activeTool, setActiveTool] = useState<string | undefined>();
  const [undoable, setUndoable] = useState(false);
  const objects = useObjects(servicesManager);
  const activeObject = objects.find(o => o.active);

  // ── state subscriptions ───────────────────────────────────────────────────────────────
  useEffect(() => sessionState.subscribe(() => setSession(sessionState.get())), []);

  useEffect(() => toolboxState.subscribe(() => setUi(toolboxState.get())), []);

  // The armed tool can also change from the main toolbar, so read it from the tool group.
  useEffect(() => {
    const tick = () => {
      const viewportId = viewportGridService.getActiveViewportId();
      setActiveTool(viewportId ? toolGroupService.getActiveToolForViewport(viewportId) : undefined);
      setUndoable(objectModel.isUndoable());
    };
    tick();
    const id = setInterval(tick, 250);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      const result = await isAvailable();
      if (mounted) {
        setAvailable(result);
      }
    };
    check();
    const id = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  // Heartbeat while a session exists; release the backend slot when the tab goes away.
  useEffect(() => {
    if (!available) {
      return;
    }
    const id = setInterval(() => {
      if (document.visibilityState === 'visible' && sessionState.get().status === 'ready') {
        commandsManager.run('nninterSessionStatus');
      }
    }, 20000);
    const onPageHide = () => {
      if (sessionState.get().status === 'ready') {
        commandsManager.run('closeNninterSession');
      }
    };
    window.addEventListener('pagehide', onPageHide);
    return () => {
      clearInterval(id);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [available]);

  useEffect(() => {
    return () => toolboxState.set({ manualCorrectionMode: false, negative: false });
  }, []);

  const status: Status =
    available === null
      ? 'checking'
      : !available
        ? 'unavailable'
        : session.status === 'initializing'
          ? 'starting'
          : session.status === 'ready'
            ? 'ready'
            : session.status === 'error'
              ? 'error'
              : 'idle';
  const enabled = available === true;
  const brushActive = ui.manualCorrectionMode && BRUSH_TOOLS.includes(activeTool ?? '');

  // ── actions ────────────────────────────────────────────────────────────────────────────
  const notify = (message: string) =>
    uiNotificationService?.show?.({ title: 'nnInteractive', message, type: 'info' });

  const setNegative = (negative: boolean) => {
    toolboxState.set({ negative });
    if (toolboxState.get().manualCorrectionMode) {
      commandsManager.run('setToolActiveToolbar', {
        toolName: negative ? 'CircularEraser' : 'CircularBrush',
      });
    }
  };

  const disarm = () => {
    toolboxState.set({ manualCorrectionMode: false, tool: 'none' });
    commandsManager.run('setToolActive', { toolName: 'Pan' });
  };

  const togglePromptTool = (toolName: string) => {
    if (!enabled) {
      return;
    }
    if (activeTool === toolName && !toolboxState.get().manualCorrectionMode) {
      disarm();
      return;
    }
    toolboxState.set({ manualCorrectionMode: false, tool: toolName });
    commandsManager.run('setToolActive', { toolName });
  };

  const applyBrushSize = (size: number) => {
    const clamped = Math.min(BRUSH_SIZE_MAX, Math.max(BRUSH_SIZE_MIN, size));
    toolboxState.set({ brushSize: clamped });
    commandsManager.run('setBrushSize', { value: clamped, toolNames: BRUSH_TOOLS });
  };

  const toggleBrush = () => {
    if (!enabled) {
      return;
    }
    if (brushActive) {
      disarm();
      return;
    }
    if (!activeObject) {
      notify('Select an object to correct first.');
      return;
    }
    toolboxState.set({ manualCorrectionMode: true, tool: 'brush' });
    applyBrushSize(toolboxState.get().brushSize);
    commandsManager.run('setToolActiveToolbar', {
      toolName: toolboxState.get().negative ? 'CircularEraser' : 'CircularBrush',
    });
  };

  const togglePrompts = () => {
    const next = !toolboxState.get().promptsVisible;
    toolboxState.set({ promptsVisible: next });
    // Prompts are Cornerstone annotations (not measurements) — toggle them directly.
    promptModel.setPromptsVisible(next);
  };

  // Reset and delete drop the object's mask and cannot be undone.
  const confirmObjectAction = (action: string, object: ObjectRow) =>
    window.confirm(`${action} "${object.label}"? This cannot be undone.`);

  const resetObject = (object = activeObject) => {
    if (object && confirmObjectAction('Clear', object)) {
      commandsManager.run('resetSegment', {
        segmentationId: object.segmentationId,
        segmentIndex: object.segmentIndex,
      });
    }
  };

  const deleteObject = (object = activeObject) => {
    if (object && confirmObjectAction('Delete', object)) {
      commandsManager.run('deleteNninterObject', {
        segmentationId: object.segmentationId,
        segmentIndex: object.segmentIndex,
      });
    }
  };

  const newObject = () => enabled && commandsManager.run('armNextNninterObject');
  const undo = () => enabled && undoable && commandsManager.run('undoNninter');
  const run = () => enabled && commandsManager.run('nninter');

  // Both export every object of the series as one overlapping SEG.
  const exportSeg = (commandName: string) => {
    const object = activeObject ?? objects[0];
    if (object) {
      commandsManager.run({
        commandName,
        commandOptions: { segmentationId: object.segmentationId },
        context: 'SEGMENTATION',
      });
    }
  };
  const saveSeg = () => exportSeg('storeNninterSegmentation');
  const downloadSeg = () => exportSeg('downloadNninterSegmentation');

  // ── keyboard ───────────────────────────────────────────────────────────────────────────
  // Every shortcut shown in the panel is handled here; latest closures via the ref below.
  const keyActions: Record<string, () => void> = {
    p: () => togglePromptTool('Probe2'),
    b: () => togglePromptTool('RectangleROI2'),
    s: () => togglePromptTool('PlanarFreehandROI2'),
    l: () => togglePromptTool('PlanarFreehandROI3'),
    c: toggleBrush,
    t: () => setNegative(!toolboxState.get().negative),
    q: () => toolboxState.set({ liveMode: !toolboxState.get().liveMode }),
    o: togglePrompts,
    n: newObject,
    r: () => resetObject(),
    delete: () => deleteObject(),
    // Only while brushing: otherwise these stay OHIF's zoom keys.
    ...(brushActive && {
      '+': () => applyBrushSize(toolboxState.get().brushSize + 1),
      '=': () => applyBrushSize(toolboxState.get().brushSize + 1),
      '-': () => applyBrushSize(toolboxState.get().brushSize - 1),
    }),
  };
  const keyActionsRef = React.useRef(keyActions);
  keyActionsRef.current = keyActions;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = document.activeElement as HTMLElement | null;
      if (
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable
      ) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === 'z' && (event.ctrlKey || event.metaKey) && !event.shiftKey) {
        event.preventDefault();
        event.stopPropagation();
        commandsManager.run('undoNninter');
        return;
      }
      // Single keys only: leave Ctrl/Cmd/Alt combos to the browser and OHIF.
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      const action = keyActionsRef.current[key];
      if (!action || !enabled) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      action();
    };
    document.addEventListener('keydown', onKeyDown, true);
    return () => document.removeEventListener('keydown', onKeyDown, true);
  }, [enabled]);

  // ── render ─────────────────────────────────────────────────────────────────────────────
  const statusInfo = STATUS_TEXT[status];
  const toolButtonStyle = (active: boolean): React.CSSProperties => ({
    height: 'auto',
    flexDirection: 'column',
    gap: 2,
    padding: '6px 0',
    fontSize: 11,
    // Inactive tools are outlined so the armed one is the only filled button.
    border: active ? '1px solid transparent' : '1px solid rgba(90, 204, 230, 0.25)',
  });

  return (
    <PanelSection defaultOpen={true}>
      <PanelSection.Header className="flex items-center justify-between">
        <span>nnInteractive</span>
        <span
          className="text-muted-foreground flex items-center text-xs"
          style={{ gap: 6, marginLeft: 'auto', marginRight: 8 }}
          title={statusInfo.hint}
        >
          <span
            className="rounded-full"
            style={{ width: 8, height: 8, backgroundColor: statusInfo.color }}
          />
          {statusInfo.text}
        </span>
      </PanelSection.Header>

      <PanelSection.Content className="bg-muted flex-shrink-0 border-none">
        <div className="flex flex-col gap-3 px-2 py-2">
          {statusInfo.hint && (
            <div className="text-muted-foreground text-xs">
              {status === 'error' && session.lastError ? session.lastError : statusInfo.hint}
            </div>
          )}

          <div
            className={classnames('flex flex-col gap-3', {
              'pointer-events-none opacity-40': !enabled,
            })}
          >
            {/* 1. what the next prompt or brush stroke does */}
            <div className="flex flex-col gap-1">
              <SectionLabel hint={<Key>T</Key>}>Prompt</SectionLabel>
              <ToggleGroup
                type="single"
                size="sm"
                className="w-full"
                value={ui.negative ? 'negative' : 'positive'}
                onValueChange={value => value && setNegative(value === 'negative')}
              >
                <ToggleGroupItem
                  value="positive"
                  className="flex-1"
                >
                  + Positive
                </ToggleGroupItem>
                <ToggleGroupItem
                  value="negative"
                  className="flex-1"
                >
                  − Negative
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* 2. tools: four prompt types plus the manual-correction brush */}
            <div className="flex flex-col gap-1">
              <SectionLabel>Tool</SectionLabel>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 4 }}>
                {PROMPT_TOOLS.map(({ toolName, label, key, Icon }) => {
                  const active = activeTool === toolName && !ui.manualCorrectionMode;
                  return (
                    <Button
                      key={toolName}
                      size="sm"
                      variant={active ? 'default' : 'ghost'}
                      style={toolButtonStyle(active)}
                      title={`${label} prompt (${key})`}
                      aria-pressed={active}
                      onClick={() => togglePromptTool(toolName)}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{label}</span>
                      <Key>{key}</Key>
                    </Button>
                  );
                })}
                <Button
                  size="sm"
                  variant={brushActive ? 'default' : 'ghost'}
                  style={toolButtonStyle(brushActive)}
                  title="Correct the selected object by hand (C). Negative erases."
                  aria-pressed={brushActive}
                  disabled={!activeObject}
                  onClick={toggleBrush}
                >
                  <Brush className="h-5 w-5" />
                  <span>Brush</span>
                  <Key>C</Key>
                </Button>
              </div>
              {brushActive && (
                <div
                  className="flex items-center gap-2"
                  style={{ paddingTop: 4 }}
                >
                  <Label htmlFor="nninter-brush-size">Size</Label>
                  <input
                    id="nninter-brush-size"
                    type="range"
                    className="flex-1"
                    min={BRUSH_SIZE_MIN}
                    max={BRUSH_SIZE_MAX}
                    value={ui.brushSize}
                    onChange={e => applyBrushSize(Number(e.target.value))}
                  />
                  <span
                    className="text-muted-foreground text-xs"
                    style={{ minWidth: 40 }}
                  >
                    {ui.brushSize} mm
                  </span>
                  <Key>− +</Key>
                </div>
              )}
            </div>

            {/* 3. when prompts are sent and whether they stay visible */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="nninter-auto-run"
                  className="flex items-center gap-2"
                >
                  Run on each prompt <Key>Q</Key>
                </Label>
                <Switch
                  id="nninter-auto-run"
                  checked={ui.liveMode}
                  onCheckedChange={liveMode => toolboxState.set({ liveMode })}
                />
              </div>
              {!ui.liveMode && (
                <Button
                  size="sm"
                  variant="default"
                  className="w-full"
                  onClick={run}
                >
                  Run prompts
                </Button>
              )}
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="nninter-show-prompts"
                  className="flex items-center gap-2"
                >
                  Show prompts <Key>O</Key>
                </Label>
                <Switch
                  id="nninter-show-prompts"
                  checked={ui.promptsVisible}
                  onCheckedChange={togglePrompts}
                />
              </div>
            </div>

            <div className="border-primary/20 border-t" />

            {/* 4. objects: pick one to refine; actions apply to the selected one */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Label>Objects</Label>
                <Button
                  size="sm"
                  variant="ghost"
                  className="gap-1"
                  onClick={newObject}
                >
                  <Icons.Add />
                  New object <Key>N</Key>
                </Button>
              </div>
              <ObjectList
                objects={objects}
                onSelect={async object => {
                  await commandsManager.run('loadSegmentForRefinement', {
                    segmentationId: object.segmentationId,
                    segmentIndex: object.segmentIndex,
                  });
                  commandsManager.run('jumpToSegment');
                }}
                onToggleVisible={object =>
                  setObjectVisible(servicesManager, object, !object.visible)
                }
                onRename={object =>
                  commandsManager.run('editSegmentLabel', {
                    segmentationId: object.segmentationId,
                    segmentIndex: object.segmentIndex,
                  })
                }
                onColor={object =>
                  commandsManager.run('editSegmentColor', {
                    segmentationId: object.segmentationId,
                    segmentIndex: object.segmentIndex,
                  })
                }
                onDelete={deleteObject}
              />
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant="secondary"
                  className="flex-1 gap-1"
                  disabled={!undoable}
                  title="Undo the last prompt on the selected object"
                  onClick={undo}
                >
                  Undo <Key>Ctrl+Z</Key>
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="flex-1 gap-1"
                  disabled={!activeObject}
                  title="Clear the selected object's mask and prompts"
                  onClick={() => resetObject()}
                >
                  Clear <Key>R</Key>
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="flex-1 gap-1"
                  disabled={!activeObject}
                  title="Delete the selected object"
                  onClick={() => deleteObject()}
                >
                  Delete <Key>Del</Key>
                </Button>
              </div>
            </div>

            <div className="border-primary/20 border-t" />

            {/* 5. result: all objects as one overlapping DICOM SEG */}
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="default"
                className="flex-1"
                disabled={!objects.length}
                title="Store all objects as one DICOM SEG in the PACS"
                onClick={saveSeg}
              >
                Save as DICOM SEG
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={!objects.length}
                aria-label="Download DICOM SEG"
                title="Download all objects as a DICOM SEG file"
                onClick={downloadSeg}
              >
                <Icons.Download />
              </Button>
            </div>
          </div>
        </div>
      </PanelSection.Content>
    </PanelSection>
  );
}
