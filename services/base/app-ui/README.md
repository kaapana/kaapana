# app-ui

One of the Kaapana view apps (Vue 3 + Vuetify 3 + Vite SPA, served by nginx and
embedded as an iframe by the `portal-ui` shell). It lists the platform's active
applications and backs **two** menu entries under the shell's *Workflows*
section: **Tasks** (`/tasks`) — workflow-triggered apps awaiting user input —
and **Apps** (`/apps`) — project-wide running apps. One container serves both;
the route's `meta.mode` selects which set `ActiveApplications.vue` renders.

## Features

- **Two routes, one view.** `/tasks` shows apps with `from_workflow_run: true`
  scoped to the selected project; `/apps` shows the project-wide apps whose
  ingress paths match `/applications/project/<id>/release/…` and
  `from_workflow_run: false`. `/` redirects to `/tasks`.
- **Ready / pending / error affordances.** Each app's pods are classified into
  `ready` / `pending` / `error` (`podStatus`); the Open button changes color,
  icon, and label (`Open` / `Starting…` / `Error`) to match, with a per-pod
  status tooltip.
- **Open in new tab.** A ready app opens its path directly in a new tab; a
  pending or errored app instead opens a status dialog (with pod detail on
  error) offering *Visit anyway*.
- **Finish interaction** (Tasks only). A confirm dialog then a POST that
  removes the row optimistically; the release name is remembered so the next
  poll can't re-add it before the backend uninstall completes. Failures surface
  in an error dialog.
- **Polling.** The active-applications list is re-fetched every 10 s; an open
  status dialog re-derives its app from the fresh list, so it updates live as
  the app moves pending → ready/error.
- **Sorting** by name or start date, ascending/descending.
- **Menu badge** (Tasks entry): the shell renders a count badge from the
  chart's `kaapana.ai/ui.badge-path` (see below) — polled by the shell, not by
  this app.

## Backend endpoints

Every call this app makes at runtime (directly or via `@kaapana/base-ui`
internals it triggers). The shared `httpClient` interceptor rewrites only URLs
matching `^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/`
onto `/project/<short_id>/…`; the other calls are **not** project-prefixed.

| Method | Path | Purpose | Project-prefixed |
|---|---|---|---|
| GET | `/oauth2/userinfo` (prod) · `/jsons/testingAuthenticationToken.json` (dev) | Auth check before each route (`AuthService.getToken`) | no |
| GET | `/aii/users/current` | Resolve the current user (project store) | no |
| GET | `/aii/users/<id>/projects` (non-admin) · `/aii/projects` (admin) | List the user's projects to resolve the URL slug | no |
| GET | `/kube-helm-api/active-applications` | The active-applications list (10 s poll) | **yes** |
| POST | `/kube-helm-api/complete-active-application` | Finish a workflow interaction (`{ release_name }`) | **yes** |

Menu-badge endpoint (polled by the shell, declared in
`app-ui-chart/templates/service.yaml` on the **Tasks** ingress only, not Apps):

| Method | Path | Purpose |
|---|---|---|
| GET | `/kube-helm-api/pending-applications-count` | `kaapana.ai/ui.badge-path` — count badge on the Tasks entry |

## Development

`@kaapana/base-ui` is a `file:` dependency consumed as its built `dist/`, so
build the library first (and re-run the build after any change to its `src/`):

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build
```

Then run this view from its `docker/files`:

```bash
cd services/base/app-ui/docker/files
npm ci
npm run dev              # Vite dev server on http://localhost:5000 (strictPort)
```

In the platform the view is reached through the shell at
`/project/<short_id>/app-ui/` — the shell owns the chrome and the project
prefix. The dev/preview server strips the `/project/<short_id>/` prefix like
traefik does (see `vite.config.ts`), so the project-scoped URL works locally
too; served without the prefix (`/app-ui/`), the project store redirects onto
the user's first project.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route`.

```bash
cd services/base/app-ui/docker/files
npx playwright test      # fixed port 4301 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing.

Suites: `applications-list`, `open-application`, `finish-interaction`,
`polling`, `project-scope`.
