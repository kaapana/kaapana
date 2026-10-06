# portal-ui

The Kaapana **shell** (Vue 3 + Vuetify 3 + Pinia + Vite SPA, served by nginx).
It owns the platform chrome at `/` — navigation drawer, project selector,
settings, notifications, about, idle logout — and renders every view inside a
single same-origin iframe (`src/views/IframeHost.vue`). It contains no view
code: the menu is built at runtime from `GET /portal-api/menu`, and the shell
talks to the embedded views only through the document URL, `localStorage` and a
small `postMessage` protocol.

Like the view apps, `portal-ui` depends on `@kaapana/base-ui` (a `file:` link
to `../../../base-ui/docker/files`, see Development). From the library it takes
what must look and behave the same in the shell and in the views: the theme,
the typeface, the icon map, `ConfirmDialog`, `ErrorDetailsDialog`,
`apiErrorInfo` and the OPA helper. Its own project, auth and HTTP code stays,
because the library's versions are written for a view running inside the
shell. For example, `src/api/http.ts` adds the project prefix like the
library's `utils/httpClient.ts`, but also reloads the page when the session has
expired.

## Features

- **Runtime menu.** `stores/menu.ts` polls `/portal-api/menu` every 15 s and
  filters it client-side against the OPA policy data (base-ui's
  `checkAuthR`). The filter is cosmetic — the gateway is the real boundary.
  Sections collapse; the collapsed rail substitutes a text glyph for a section
  child with no `ui.icon`.
- **Count badges.** Entries declaring `kaapana.ai/ui.badge-path` get a count
  badge, polled on every menu poll and re-polled (with the previous project's
  counts cleared first) whenever the `/project/<slug>` route param changes. A
  collapsed section shows the sum of its entries' badges.
- **Project selection lives in the URL.** Canonical routes are
  `/project/<short_id>/<section>/<entry>`. `ProjectSelector.vue` swaps the
  prefix with `router.push` — the shell is never reloaded, only the iframe is.
  `stores/project.ts` is synced *from* the URL by the router guard;
  `localStorage["project"]` is only the cross-session default for a tab opened
  without a prefix.
- **Project-scoped API calls.** `api/http.ts`'s request interceptor rewrites
  any URL matching
  `^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` onto
  `/project/<slug>/…`, reading the slug from `location.pathname` — deliberately
  **not** from `localStorage`, which another tab rewrites on a project switch
  and would cross-tab mis-scope the call.
- **The router predicts iframe reloads.** `utils/iframeSrc.ts`'s
  `iframeSrcFor()` is shared between `IframeHost.vue` and the router guard, so
  the guard can tell whether a navigation would replace the iframe document and
  raise the unsaved-changes confirm before it does.
- **postMessage protocol** (same-origin checked in `App.vue`):
  `kaapana:view-dirty` (a view reports unsaved state),
  `kaapana:navigate` (a view asks the shell to open another entry; an entry the
  menu cannot offer raises `ViewUnavailableDialog` instead of bouncing
  silently), `kaapana:project-switch` (a view asks for a project switch,
  routed through the guard so the dirty confirm still runs), and
  `kaapana:shell-refresh` (a view that changed the menu or the project list
  asks the shell to re-read both, debounced).
- **Settings.** `stores/settings.ts` merges the DB copy over
  `static/defaultUIConfig.ts` and seeds `localStorage["settings"]` **before**
  the first iframe mounts — the views read that key synchronously. The theme
  choice (System / Light / Dark) and the Dev Mode switch sit in the settings
  dialog header and apply at once. "System" follows the browser's colour
  scheme, and follows a change of it without a reload. The views still read
  the `darkMode` flag, which the shell derives from the choice. Settings stored
  before the choice existed have only `darkMode`: `false` becomes Light, and
  `true` becomes System, because the old dialog stored its default `true` on
  every Save, so it was never a choice. Dev Mode additionally reveals each
  entry's `ui.dev-links`.
- **Notifications.** A bell badged with the server-side unread `total`, opening
  a dialog that groups the list by topic and pages in 20 at a time as it is
  scrolled, plus a WebSocket feed (`api/notifications.ts`) that reconnects with
  a capped exponential backoff and only resets the backoff once a socket has
  stayed open for 30 s.
- **Idle logout.** `composables/useIdleLogout.ts` — one module-level timer
  (`VITE_APP_IDLE_TIMEOUT`, default 30 min) armed in `App.vue`'s `onMounted`
  *before* anything that can reject. `IframeHost` re-attaches the activity
  listeners to the iframe document on every `load`, because in-iframe activity
  never bubbles to the parent and each in-iframe navigation drops them.
- **Login-in-iframe escape.** An expired session 302s to Keycloak on the same
  host, so the login page can render inside the iframe. `api/http.ts` detects
  the Keycloak auth URL (on `responseURL`, not on a `text/html` body) and
  reloads the top window, suppressing repeats within a 30 s window recorded in
  `sessionStorage`.
- **Nested-shell detection.** `main.ts` refuses to boot when
  `window.self !== window.top` (a view URL fell through the gateway back to the
  SPA) and renders a plain notice instead of nesting menu inside menu. Vuetify
  has not run yet, so the notice takes its colours from the shared theme and
  the theme choice stored in `localStorage`.
- **Failure details.** Clicking an error toast opens base-ui's
  `ErrorDetailsDialog`: status, request, backend message and request id, with
  a copy button. Failures shown in place (boot, menu, project list, About
  version, settings field list) open the same dialog with a *Details* button.
  See `utils/notifyFailure.ts` and `stores/failureDetails.ts`.
- **Corner controls.** Two buttons in the bottom-right corner of the view,
  shown while the mouse is over that corner or one of them has keyboard focus:
  reload (behind the unsaved-changes confirm) and open in a new tab. Both use
  the page the view is *currently* on, not the entry's start page. Tab from the
  drawer reaches them before anything inside the view.
- **Navigation contract and bookmark redirects.** Views address shell routes
  as `/web/<section>/<entry>` (`/web/-/<entry>` for a top-level entry):
  base-ui's `navigateShell` posts that path, and the router redirects it to
  `/project/<short_id>/<section>/<entry>`, keeping the query string. The routes
  of the old monolith (`/datasets`, `/workflows`, …) redirect too, but only for
  old bookmarks. They are due for removal in <release TBD>, together with their
  `data.rego` grants and `clearLegacyProjectCookie`.

## Backend endpoints

Every runtime network call. Only `/kaapana-backend/…` and the badge endpoints
are project-prefixed — `api/http.ts` rewrites URLs matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/`; everything
else is requested verbatim. The **Legacy** column marks the calls into
`kaapana-backend`, the API of the old monolith, and says why each one is still
needed.

| Method | Path | Purpose | Project-prefixed | Legacy |
|---|---|---|---|---|
| GET | `/oauth2/userinfo` (prod) · `/jsons/testingAuthenticationToken.json` (dev) | Userinfo JWT → username, roles, groups (`stores/auth.ts`) | no | — |
| GET | `/kaapana-backend/open-policy-data` | OPA policy data for the client-side menu filter | **yes** | **yes** — goes away once portal-api filters the menu (follow-up issue) |
| GET | `/portal-api/menu` · `/portal-api/menu?fresh=1` | The menu itself; polled every 15 s. `fresh=1` bypasses portal-api's cache and is sent only after a view's `kaapana:shell-refresh` | no | — |
| GET | `/aii/users/current` | Resolve the current AII user | no | — |
| GET | `/aii/users/<id>/projects` (non-admin) · `/aii/projects` (admin) | The user's projects; re-polled on the menu cadence | no | — |
| GET | `/kaapana-backend/settings` | Persisted settings, merged over the defaults and seeded into `localStorage` | **yes** | **yes** — no newer service stores user settings yet |
| PUT | `/kaapana-backend/settings` | Save the whole settings object (dialog *Save* / *Restore defaults*) | **yes** | **yes** — as above |
| PUT | `/kaapana-backend/settings/item` | Save one key (the theme choice, the Dev Mode switch) | **yes** | **yes** — as above |
| GET | `/kaapana-backend/dataset/fields` | DICOM tag → OpenSearch field mapping for the settings dialog | **yes** | **yes** — moves with the Dataset Configuration tab to `data-gallery-ui` (follow-up issue) |
| GET | `/notifications/v2/?limit=20&cursor=…` | One page of notifications | no | — |
| PUT | `/notifications/v2/<id>/read` | Mark one notification read | no | — |
| PUT | `/notifications/v2/read` | Mark every notification read (dialog *Mark all as read*) | no | — |
| WS | `/notifications/ws` | Live notification events (`new` / `read` / `read_all`) | no | — |
| GET | `/jsons/commonData.json` | Chart version for the drawer header and the About dialog; served by this app's own nginx from the `portal-ui-config` ConfigMap | no | — |
| GET | `<entry.badgePath>` | Count badge of any menu entry declaring `kaapana.ai/ui.badge-path` (today only `/kube-helm-api/pending-applications-count`) | **yes**, when the path matches the rewrite | — |
| — | `/kaapana-backend/oidc-logout` | Logout; a top-level `location.href`, not an XHR | no | **yes** — no newer logout endpoint yet |

These are the last calls into the old monolith's API; the shell adds no new
ones.

The notifications base path is the only configurable one
(`VITE_APP_NOTIFICATIONS_API_ENDPOINT`, default `/notifications`); the rest are
literals.

## Development

Build `@kaapana/base-ui` first: the shell imports its built `dist/`, which is
not committed. CI's `ui_unit_tests` and `ui_e2e_tests` jobs do the same.

```bash
cd services/base/base-ui/docker/files
npm ci && npm run build
cd ../../../portal-ui/docker/files
npm ci
npm run dev        # Vite dev server on http://localhost:5173 (strictPort)
```

`vite.config.ts` sets `base: '/'` — the shell owns the root path, which is why
it cannot coexist with the legacy landing page. Standalone it answers at
`http://localhost:5173/`; the router's `unscoped` guard immediately re-targets
that onto `/project/<short_id>/`, taking the project from the API. Backend
calls are not proxied, so a standalone dev server needs either a running
platform behind a proxy or the Playwright mock backend (below).

Other scripts: `npm run build` (runs `vue-tsc` over `tsconfig.json` **and**
`tsconfig.e2e.json`, so a type error in a spec fails the build),
`npm run preview`. Formatting and linting run from the repository root, see
[Code Formatting](../../../docs/source/development_guide/code_formatting.rst).

## Tests

Two suites. Both are self-contained — no backend and no cluster.

**Unit (vitest, jsdom)** — `src/**/__tests__/*.spec.ts`, for the pieces that
are awkward to drive through a browser: the project-prefix rewriting and the
login-reload logic in `api/http.ts`, the WebSocket backoff in
`api/notifications.ts`, the OPA helper from base-ui (which has no test runner),
the idle-logout timer, the stores, the failure toast, the theme plugin, and
`SettingsDialog` mounting with settings stored by older versions. This is the
only app in the platform with such a suite; CI runs it as `ui_unit_tests`.

```bash
cd services/base/portal-ui/docker/files
npm run test:unit
```

**End-to-end (Playwright)** — `tests/e2e`, mock-backed:
`fixtures/mock-backend.ts` intercepts every backend call with `page.route` and
serves fixture data typed from the app's own `src/types`.

```bash
cd services/base/portal-ui/docker/files
npx playwright test    # fixed port 4300 (views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build — set `CI=1` to exercise what CI actually does,
since `playwright.config.ts` branches on it for the reporter, the web-server
command, retries and `reuseExistingServer`.

Suites: `about-dialog`, `boot-failure`, `corner-controls`, `dev-mode`,
`iframe-loading`, `login-in-iframe`, `menu-badge`, `nav-drawer`,
`notifications`, `presentation`, `project-refresh`, `project-selector`,
`routing`, `settings`, `shell-boot`, `theme-toggle-selection`, `user-menu`,
`view-dirty`, `view-messages`.
