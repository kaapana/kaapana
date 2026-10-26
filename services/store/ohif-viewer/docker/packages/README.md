# Local OHIF Packages

The Dockerfile copies these packages into the fetched OHIF workspace, registers them in
`pluginConfig.json` (`../register-nninteractive.js`), and adds their lockfile importers
(`../pnpm-lock.nninteractive.patch`) before `pnpm install --frozen-lockfile`.

| Package | Copied to | Owns |
|---|---|---|
| `extension-nninteractive` | `/src/extensions/nninteractive` | A `model/` layer (session/image/object/prompt/coordinate-mapping/segmentation-bridge) under a thin command layer, plus panels, prompt tools, icons, customizations, metadata providers, and runtime subscriptions. |
| `mode-nninteractive` | `/src/modes/nninteractive` | Layout, toolbar sections/buttons, hotkeys, and tool-group setup. |

nnInteractive runs on stock OHIF 3.13 / Cornerstone 5: put behavior in these packages and use OHIF's
extension, mode, and customization seams rather than patching OHIF or Cornerstone sources.

## Upgrading OHIF

When `OHIF_COMMIT` in the Dockerfile changes, regenerate the lockfile patch: in the new OHIF checkout,
copy both packages in, run `node register-nninteractive.js` and `pnpm install --no-frozen-lockfile`,
then save `git diff pnpm-lock.yaml` as `pnpm-lock.nninteractive.patch`. Keep the dependency versions
in both `package.json` files aligned with OHIF's own extensions.
