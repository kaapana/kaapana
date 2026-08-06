# workflow-list-ui

The **Workflow List** view — one of the Kaapana view apps (Vue 3 + Vuetify 3 +
Vite SPA, served by nginx and embedded as a same-origin iframe by the
`portal-ui` shell, discovered at runtime via `kaapana.ai/ui.*` Ingress
annotations). It monitors workflows and their jobs, watches their states, and
acts on them (abort/restart/delete/manual-start).

## Features

- **Server-paged workflow table** (`WorkflowTable.vue`, `v-data-table-server`):
  name, ID, dataset (`name(access_level)`), created/updated, username, owner
  instance, status chips, actions. Search and pagination are server-driven —
  every options change re-queries `/workflows`. Search is **not** debounced:
  the search watch emits `update:options` synchronously on every input event,
  so each keystroke costs one `GET /workflows`.
- **Per-state job-count chips** in the Status column: colored counts
  (queued/scheduled/pending/running/finished/failed) derived from the
  workflow's `workflow_jobs` status list. Clicking a chip loads that
  workflow's jobs filtered to that state.
- **Row expansion → job table** (`JobTable.vue`): expanding a workflow fetches
  its jobs and renders a nested `v-data-table` (dag id, created/updated, runner
  and owner instance, conf, status, logs, actions). Only one row expands at a
  time. If a workflow reports no jobs, an existence check warns via a toast.
- **Job status chips + description tooltip**: colored status button whose
  tooltip shows the per-operator state JSON (parsed, sorted by `start_date`).
- **Conf dialog**: a mail icon per job opens a dialog with the pretty-printed
  `conf_data`.
- **Workflow actions** (local, non-service, automatic workflows only): abort,
  restart, delete. Non-automatic workflows show a manual-start (play) button
  instead; service workflows and remote workflows show an info icon (no
  actions). Each action toasts success/error.
- **Job actions** (jobs owned by the local instance): abort, restart, delete.
  External jobs allow abort only; other remote jobs show a no-actions icon.
- **Workflow-engine (Airflow) links** — `window.open` browser navigations, not
  API calls: a toolbar button to `/flow/home`; per-job "dag_run details" to
  `/flow/dags/<dag_id>/grid`; and for failed jobs a "failed operator logs" link
  to `/flow/log` (it first fetches task-instance states to locate the failed
  operator).
- **Manual remote sync**: a toolbar sync button triggers a remote-update check.
- **Auto-refresh / manual refresh**: the list re-fetches every 15 s
  (hardcoded; `TODO` to move into settings) and via a toolbar refresh button.
  Only the explicit toolbar refresh toasts on success, whether or not a search
  term is active; the background poll stays silent on success. Either path
  toasts on error.
- **Theme-aware**: chip colors adapt to the shell's dark/light mode.

## Backend endpoints

Every runtime call. All `/kaapana-backend/client/*` calls go through
`@kaapana/base-ui`'s `kaapanaApiService` and are **project-prefixed**: the
shared `httpClient` interceptor rewrites URLs matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` to
`/project/<short_id>/…` (short_id from the document URL). The auth call is the
only one **not** prefixed (its path does not match the regex). There is no
project store and no `/aii` call.

| Method | Path | Purpose | Project-prefixed |
| --- | --- | --- | --- |
| GET | `/kaapana-backend/client/workflows` | List workflows; body is the tuple `[rows, totalCount]`. Params `limit`, `offset`, `search`. Drives the table, polling, search, paging. | yes |
| GET | `/kaapana-backend/client/kaapana-instance` | Fetch the local instance (`getLocalInstance`, on mount). | yes |
| GET | `/kaapana-backend/client/jobs` | Jobs of a workflow. Called with `{workflow_name, status}` on expand / chip click, and `{workflow_name, limit:1}` as an existence check. | yes |
| PUT | `/kaapana-backend/client/workflow` | Abort / restart / manual-start a workflow. Body `{workflow_id, workflow_status}` with status `abort` / `scheduled` / `confirmed`. | yes |
| DELETE | `/kaapana-backend/client/workflow` | Delete a workflow (`{workflow_id}`). | yes |
| PUT | `/kaapana-backend/client/job` | Abort / restart a single job. Body `{job_id, status, description}` with status `abort` / `scheduled`. | yes |
| DELETE | `/kaapana-backend/client/job` | Delete a single job (`{job_id}`). | yes |
| GET | `/kaapana-backend/client/get-job-taskinstances` | Task-instance states for a job (`{job_id}`); used to find the failed operator for the log link. | yes |
| GET | `/kaapana-backend/client/check-for-remote-updates` | Manual sync with remote instances (`syncRemoteInstances`, sync button). | yes |
| GET | `/oauth2/userinfo` (prod) / `/jsons/testingAuthenticationToken.json` (dev) | Auth check in the router guard before each navigation. Dev builds hit the static token file; prod builds hit the oauth2 proxy. | **no** |

The first `/workflows` load is not from `onMounted` (which only starts the 15 s
interval); it is the `v-data-table-server`'s `@update:options` emit on mount →
`onOptions` → `getClientWorkflows`.

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
cd services/base/workflow-list-ui/docker/files
npm ci
npm run dev          # Vite dev server on http://localhost:5000
```

Served standalone the app lives under `/workflow-list-ui/`. In the platform it
is reached through the shell at `/project/<short_id>/workflow-list-ui/` — the
document prefix is the project selection; the dev/preview server strips the
`/project/<short_id>/` prefix like traefik does (see `vite.config.ts`), so the
project-scoped URL works locally too.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route` (fixture shapes are imported from `src/types` so contract drift
fails type-check).

```bash
cd services/base/workflow-list-ui/docker/files
npx playwright test    # fixed port 4309 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing.

Suites: workflow list & states, detail expansion & conf dialog, workflow
actions & sync, job actions, search & pagination, polling, project scoping.
