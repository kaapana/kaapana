# @kaapana/mode-nninteractive

Kaapana OHIF mode for the nnInteractive workflow.

This package owns workflow composition: layout, toolbar sections, toolbar buttons, hotkeys, and
Cornerstone tool-group setup. Product behavior belongs in `../extension-nninteractive`.

## Entry Points

| File | Role |
|---|---|
| `src/index.ts` | OHIF mode factory. Defines route name, extension dependencies, mode layout, toolbar sections, hotkey migration, and mode enter/exit behavior. |
| `src/initToolGroups.js` | Tool-group setup for prompt tools, segmentation tools, manual correction brush/eraser, and standard viewer tools. |
| `src/toolbarButtons.ts` | Toolbar button definitions and nested button sections. |
| `src/id.ts` | Stable mode id. |

## Responsibilities

Keep these concerns here:

- default mode layout and panel composition
- which panel module ids are used
- toolbar section creation
- toolbar button definitions
- active/enabled/passive tool membership
- prompt/manual brush tool-group registration
- hotkey defaults and hotkey migration

Do not put backend calls, prompt payload extraction, segmentation store/download behavior, or panel
business logic in this package. Those belong in `@kaapana/extension-nninteractive`.

## Extension Dependency

The mode depends on:

```ts
'@kaapana/extension-nninteractive': '^3.10.4'
```

The key panel bridge is:

```ts
'@kaapana/extension-nninteractive.panelModule.panelSegmentationWithTools'
```

That panel renders the extension-owned AI toolbox above the extension-owned segmentation panel/table.

## Hotkeys

`src/index.ts` rewrites selected stock hotkeys and adds nnInteractive defaults. It also clears stale
stored browser hotkey preferences when `HOTKEY_PREFERENCES_VERSION` changes.

If hotkeys change:

1. update `migrateHotkeyBindings`
2. bump `HOTKEY_PREFERENCES_VERSION`
3. verify a browser with old localStorage gets the new bindings

## Tool Groups

`src/initToolGroups.js` must stay aligned with prompt tools registered by the extension:

- `Probe2`
- `RectangleROI2`
- `PlanarFreehandROI2`
- `PlanarFreehandROI3`

If a prompt tool is renamed or replaced, update both packages together.

## Smoke Test After Changes

Verify:

- viewer opens directly into this mode
- right panel opens with AI toolbox + segmentation panel
- toolbar sections render
- prompt tools activate from toolbar
- hotkeys work after a fresh load and after stale localStorage
- manual brush add/erase tools activate correctly
- viewport hover activation still lets first click draw/use the active tool
