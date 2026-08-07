# portal-ui

The Kaapana **shell** (Vue 3 + Vuetify 3 + Pinia + Vite SPA, served by nginx).
It owns the platform chrome at `/` — navigation drawer, project selector,
settings, notifications, about, idle logout — and renders every view inside a
single same-origin iframe (`src/views/IframeHost.vue`). It contains no view
code: the menu is built at runtime from `GET /portal-api/menu`, and the shell
talks to the embedded views only through the document URL, `localStorage` and a
small `postMessage` protocol.

Unlike the nine view apps, `portal-ui` declares no `@kaapana/base-ui`
dependency — so there is no library to build before it, and no `resolve.dedupe`
in its `vite.config.ts`. Its `src/api/http.ts` carries the same
`PROJECT_SCOPED` regex and project-prefixing request interceptor as the
library's `utils/httpClient.ts`, plus a response interceptor for the
expired-session reload that the library has no counterpart for;
`src/utils/opa.ts` has no counterpart in the library at all. It is also the
only app in the platform with a vitest suite.

## Features

- **Runtime menu.** `stores/menu.ts` polls `/portal-api/menu` every 15 s and
  filters it client-side against the OPA policy data (`utils/opa.ts`,
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
  silently), and `kaapana:project-switch` (a view asks for a project switch,
  routed through the guard so the dirty confirm still runs).
- **Settings.** `stores/settings.ts` merges the DB copy over
  `static/defaultUIConfig.ts` and seeds `localStorage["settings"]` **before**
  the first iframe mounts — the views read that key synchronously. Dark Mode
  and Dev Mode are switches in the settings dialog header and apply
  immediately; Dev Mode additionally reveals each entry's `ui.dev-links`.
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
  SPA) and renders a plain notice instead of nesting menu inside menu. It reads
  the persisted dark-mode flag straight out of `localStorage` for that notice,
  since Vuetify has not run yet.
- **Corner controls.** A hover hotspot in the iframe's bottom-right corner
  offers reload (guarded by the unsaved-changes confirm) and open-in-new-tab of
  the URL the iframe is *currently* on, not the entry's start page.
- **Legacy redirects.** The old monolith's `/web/<section>/<entry>` bookmarks
  and its flat routes (`/datasets`, `/workflows`, …) redirect onto the new
  slugs, preserving the query string.

## Backend endpoints

Every runtime network call. Only `/kaapana-backend/…` and the badge endpoints
are project-prefixed — `api/http.ts` rewrites URLs matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/`; everything
else is requested verbatim.

| Method | Path | Purpose | Project-prefixed |
|---|---|---|---|
| GET | `/oauth2/userinfo` (prod) · `/jsons/testingAuthenticationToken.json` (dev) | Userinfo JWT → username, roles, groups (`stores/auth.ts`) | no |
| GET | `/kaapana-backend/open-policy-data` | OPA policy data for the client-side menu filter | **yes** |
| GET | `/portal-api/menu` | The menu itself; polled every 15 s | no |
| GET | `/aii/users/current` | Resolve the current AII user | no |
| GET | `/aii/users/<id>/projects` (non-admin) · `/aii/projects` (admin) | The user's projects; re-polled on the menu cadence | no |
| GET | `/kaapana-backend/settings` | Persisted settings, merged over the defaults and seeded into `localStorage` | **yes** |
| PUT | `/kaapana-backend/settings` | Save the whole settings object (dialog *Save* / *Restore defaults*) | **yes** |
| PUT | `/kaapana-backend/settings/item` | Save one key (the Dark Mode / Dev Mode switches) | **yes** |
| GET | `/kaapana-backend/dataset/fields` | DICOM tag → OpenSearch field mapping for the settings dialog | **yes** |
| GET | `/notifications/v2/?limit=20&cursor=…` | One page of notifications | no |
| PUT | `/notifications/v2/<id>/read` | Mark one notification read | no |
| WS | `/notifications/ws` | Live notification events (`new` / `read`) | no |
| GET | `/jsons/commonData.json` | Chart version for the drawer header and the About dialog; served by this app's own nginx from the `portal-ui-config` ConfigMap | no |
| GET | `<entry.badgePath>` | Count badge of any menu entry declaring `kaapana.ai/ui.badge-path` (today only `/kube-helm-api/pending-applications-count`) | **yes**, when the path matches the rewrite |
| — | `/kaapana-backend/oidc-logout` | Logout; a top-level `location.href`, not an XHR | no |

The notifications base path is the only configurable one
(`VITE_APP_NOTIFICATIONS_API_ENDPOINT`, default `/notifications`); the rest are
literals.

## Development

The shell has no `@kaapana/base-ui` dependency, so there is nothing to build
first:

```bash
cd services/base/portal-ui/docker/files
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
`npm run preview`, `npm run lint`, `npm run format`.

## Tests

Two suites. Both are self-contained — no backend and no cluster.

**Unit (vitest, jsdom)** — `src/**/__tests__/*.spec.ts`, for the pieces that
are awkward to drive through a browser: the project-prefix rewriting and the
login-reload logic in `api/http.ts`, the WebSocket backoff in
`api/notifications.ts`, the OPA filter in `utils/opa.ts`, and the menu,
notifications and project stores. This is the only app in the platform with
such a suite; CI runs it as `ui_unit_tests`.

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

Suites: `about-dialog`, `boot-failure`, `dev-mode`, `iframe-loading`,
`login-in-iframe`, `menu-badge`, `nav-drawer`, `notifications`,
`project-refresh`, `project-selector`, `routing`, `settings`, `shell-boot`,
`view-dirty`, `view-messages`.
