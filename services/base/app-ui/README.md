# app-ui

One of the Kaapana view apps (Vue 3 + Vuetify 3 + Vite SPA, served by nginx and
embedded as an iframe by the `portal-ui` shell). It lists the platform's active
applications and backs **two** menu entries under the shell's *Workflows*
section: **Tasks** (`/tasks`) — workflow-triggered apps awaiting user input —
and **Apps** (`/apps`) — project-wide running apps. One container serves both;
the route's `meta.mode` selects which set `ActiveApplications.vue` renders.

The view is `src/views/ActiveApplications.vue`, supported by:

| Path | Purpose |
| --- | --- |
| `src/api/applications.ts` | The kube-helm calls, mapped from the wire format to `ActiveApplication`. |
| `src/utils/podStatus.ts` | Classifies an application as ready, pending or error from its pods. |
| `src/utils/notifyFailure.ts` | Reports a failed action as a notification that carries its details. |
| `src/stores/failureDetails.ts` | The one failure-details dialog, opened from a notification, alert or empty state. |

The theme, typeface, icon map, `ConfirmDialog` and `ErrorDetailsDialog` come
from `@kaapana/base-ui`.

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
  error) offering *Open anyway*. Cancel takes the initial focus.
- **Finish interaction** (Tasks only). A `ConfirmDialog` states what finishing
  does, then a POST removes the row; the release name is remembered so the
  next poll can't re-add it before the backend uninstall completes. While the
  request runs, the row's controls are disabled. A failure arrives as a
  transient notification; selecting it opens `ErrorDetailsDialog` with the
  backend message.
- **Loading, empty and failure states.** A skeleton shows until the first
  response arrives. An empty list says why it is empty, per route. A failed
  first load (applications or project) shows an error state with *Try again*
  and *Details*. A failed poll after a successful load keeps the last list and
  shows an inline alert until a poll succeeds.
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

The view calls no legacy `kaapana-backend` endpoint: its own calls go to
`kube-helm-api`, the rest are the auth and `aii` lookups inside
`@kaapana/base-ui`.

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

Specs by concern:

| Spec | Covers |
| --- | --- |
| `boot` | fresh-profile boot |
| `applications-list` | per-route lists and affordances, display names, apps without paths, sorting, auth failure |
| `open-application` | opening ready apps, the status dialog and its live update |
| `finish-interaction` | the finish payload, cancelling, no double submit, the failure notification and its details |
| `states` | loading skeleton, empty states, failed first load with retry, failed project lookup |
| `polling` | status changes across polls, the stale-list alert |
| `project-scope` | every call carries the `/project/<slug>/` prefix; the unscoped-URL redirect |
| `guidelines` | confirmations and focus, theme and typeface, readable width, accessible names |
