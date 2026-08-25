# @kaapana/base-ui

Small shared UI library for the Kaapana frontend views (`services/base/*-ui`).
Holds components/utilities that would otherwise be copy-pasted per view —
deliberately only small, stable pieces.

- `httpClient`, `httpClientWithoutTimeout` — the shared axios instances (10 s
  timeout / none). Both rewrite calls to project-scoped services onto
  `/project/<short_id>/<service>/…` via a request interceptor.
- `AuthService` (default export), `UserinfoJwt` — `/oauth2/userinfo` token
  fetch and logout.
- `kaapanaApiService` — the kaapana-backend / kube-helm call wrappers shared
  by the views.
- `getProjectSlug()`, `getProjectBase()`, `switchProject(slug)` — the selected
  project, read from the document URL, never from storage.
- `navigateShell(path)` — ask the shell to open another view.
- `postViewDirty(dirty)` — postMessage wrapper telling the portal-ui shell the
  embedded view has unsaved in-memory state.
- `kaapanaThemeLight`, `kaapanaThemeDark`, `KAAPANA_THEME_LIGHT`,
  `KAAPANA_THEME_DARK` — the shared Vuetify theme definitions and their names.
- `createKaapanaVuetify()`, `KaapanaVuetifyOptions` — builds the shared theme,
  icon configuration and platform fonts while allowing consumer extensions.
- `kaapanaIcons`, `KaapanaIconName` — semantic names for shared action icons.
- `useAuthStore`, `User` / `useProjectStore`, `Project` — the two Pinia stores
  every view registers.
- `useShellSettings()` — follows the shell's UI settings (dark mode live, other
  changes via a remount key).

## Styles a consuming view must import

```ts
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
```

That is the whole list. In particular there is **no font import**: the platform
typeface (Roboto, weights 300/400/500) is injected by `createKaapanaVuetify()`,
so a view that uses the shared Vuetify configuration cannot ship the theme and
forget the face.

Why it works that way. Vuetify's stylesheet asks for `"Roboto", sans-serif` in 81
separate rule blocks and exposes no CSS custom property for the family, so a view
that does not provide the face silently renders in whatever the client OS
substitutes — Arial on Windows, DejaVu on Linux. Expecting each view to remember
an import did not work: none of the nine new view containers had one. The
stylesheets are imported here with `?inline` and injected as a single `<style>`
element, which costs ~174 kB of base64 inside `index.js` and buys zero font
requests and nothing for a view to remember. `@mdi/font` is deliberately *not*
handled this way — its webfont would add ~2 MB of base64.

Changing the family is not possible through the theme, for the same reason it has
to be shipped: it takes recompiling Vuetify's Sass through `$body-font-family`.

`vue`, `vuetify`, `axios`, `@kyvg/vue3-notification` and `pinia` are all
peerDependencies and none of them is ever bundled; the consuming view provides
them (see the dedupe list below).

The main `.` entry is kept free of `@koumoul/vjsf`. The workflow-triggering
component ships from a separate subpath so the six non-vjsf views aren't forced
to install vjsf:

- `@kaapana/base-ui/workflow-execution` — `{ WorkflowExecution }`, a generic
  "plug workflow-triggering into your UI" component (dataset picker, vjsf-based
  workflow form, submit). Import its styles alongside it:
  `import '@kaapana/base-ui/workflow-execution.css'`. `@koumoul/vjsf` is an
  **optional** peerDependency — only the three views using this component
  install it, and they must declare the exact pin
  `"@koumoul/vjsf": "3.26.1"` this library's peer range asks for.

## How views consume it

Each consumer declares

```json
"@kaapana/base-ui": "file:../../../base-ui/docker/files"
```

npm installs this as a symlink to this directory, and the views import the
**built** output (`dist/`). The relative path is the same in the repo and inside
the Docker build (see below). Every peer must be listed in the consumer's
`vite.config.ts` dedupe, so imports inside the linked package resolve against
the consumer's copy:

```js
resolve: {
  dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
}
```

Consumers of the `./workflow-execution` entry append `'@koumoul/vjsf'`; the
other views must not, since they do not install that optional peer. A missing
entry is a hard build failure (`Rollup failed to resolve import …`).

One-time (and after every change to `src/`):

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build          # emits dist/ — what consumers import
```

Then the usual per-view loop works unchanged from the view's `docker/files`:
`npm ci && npm run dev`, `npx playwright test`, `npm run build`.

Component development with Storybook (dev-only, not deployed, no CI job):

```bash
npm run storybook      # http://localhost:6006
```

New components: add under `src/`, export from `src/index.ts`, add a
`*.stories.ts` beside it, `npm run build`.

## Docker / kaapana-build

`docker/Dockerfile` builds the local-only base image of the FROM-chain
(`LABEL REGISTRY="local-only"` → tag `local-only/base-ui:latest`). Consumer
Dockerfiles start with `FROM local-only/base-ui:latest AS base-ui` and copy
`package.json` + `dist/` out of it:

```dockerfile
FROM local-only/base-ui:latest AS base-ui

FROM docker.io/node:lts-alpine3.23 AS build-stage
# plus the usual LABEL IMAGE / VERSION / BUILD_IGNORE that kaapana-build reads
WORKDIR /kaapana/<app>/docker/files
COPY --from=base-ui /kaapana/base-ui/docker/files/package.json /kaapana/base-ui/docker/files/package.json
COPY --from=base-ui /kaapana/base-ui/docker/files/dist /kaapana/base-ui/docker/files/dist
COPY files/package*.json ./
RUN npm install -g npm@11.16.0 && npm ci
```

Both `COPY --from` destinations are absolute and independent of the consumer's
`WORKDIR`: they reproduce this package's own `WORKDIR
/kaapana/base-ui/docker/files`. The `WORKDIR` must then sit three levels below
`/kaapana` so `file:../../../base-ui/docker/files` resolves in-image; in the repo
the same relative path works because the app is a **sibling of base-ui**, at
`services/base/<app>/docker/files`.

kaapana-build discovers the chain from the FROM line and builds base-ui first
automatically. For a plain docker build, build base-ui once yourself:

```bash
docker build -t local-only/base-ui:latest services/base/base-ui/docker
docker build services/base/workflow-execution-ui/docker
```
