# Local OHIF Packages

These packages are copied into the fetched OHIF workspace by the Dockerfile before `yarn install`.
They are the preferred home for Kaapana-owned nnInteractive behavior.

| Package | Copied to | Owns |
|---|---|---|
| `extension-nninteractive` | `/src/extensions/nninteractive` | Commands, panels, prompt tools, icons, customizations, metadata providers, and runtime subscriptions. |
| `mode-nninteractive` | `/src/modes/nninteractive` | Layout, toolbar sections/buttons, hotkeys, and tool-group setup. |

Use these packages instead of adding new source patches whenever OHIF exposes a workable extension or
mode seam. Keep `../patches` for unavoidable source-tree residue and `../node-module-patches` for
low-level Cornerstone/vtk fixes.
