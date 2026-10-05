# federated-ui

The **Instance Overview** (federation) view — one of the Kaapana view apps
(Vue 3 + Vuetify 3 + Vite SPA, served by nginx and embedded as an iframe by
the `portal-ui` shell). It lists
the local Kaapana instance and the remote runner instances it federates with,
and lets an operator add, edit, sync, and delete remotes and their allowed
DAGs/datasets. Discovered as a menu entry via `kaapana.ai/ui.*` Ingress
annotations; scoped to a project through the `/project/<short_id>/` document
prefix.

## Features

Sourced from `src/` and `tests/e2e`:

- **Instance cards** (`RunnerInstances.vue` → `KaapanaInstance.vue`) — one card
  per instance, local (`mdi-home`) or remote (`mdi-cloud-braces`), showing
  network (`protocol://host:port`), token, created/updated timestamps, verify
  SSL, fernet key, auto-sync and auto-execute flags, allowed DAGs and allowed
  datasets (as chips). Remote cards carry a freshness dot from `time_updated`
  (green <5 min, yellow <1 h, orange <5 h, else red). The list refetches on a
  15 s poll.
- **Add remote** (`AddRemoteInstance.vue`) — a dialog with two tabs: **Manual**
  (name/host/port/token/fernet/ssl fields, name+host+token required) and
  **Paste Config** (a JSON blob parsed into the same fields). Both panes stay
  mounted (`eager`) so required-field validation fires even when submitting from
  the Paste tab.
- **Edit in place** — each card field has a pencil→save inline editor; saving
  PUTs the whole instance to the local or remote endpoint. A background poll
  mid-edit does not clobber an unsaved field (the working copy reseeds from the
  prop only while nothing is being edited).
- **Sync remotes** — a toolbar button triggers a remote-update check, then
  refetches.
- **Delete remote** — trash icon → confirm dialog → delete (also drops the
  instance's jobs).
- **Copy local instance definition** — copies the local instance JSON to the
  clipboard (the shape the Paste Config tab expects on the peer side).
- Allowed-DAG and allowed-dataset pickers lazily fetch their option lists only
  when their editor is opened; datasets are filtered client-side to
  `access_level === 'project'`.

## Backend endpoints

Every call goes through the shared `httpClient` (`@kaapana/base-ui`). Its request
interceptor rewrites URLs matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` onto the
`/project/<short_id>` document prefix, so **all `kaapana-backend` calls below are
project-scoped** to `/project/<short_id>/…`; the auth calls are not.

Federation client API (`kaapanaApiService`, base path `/kaapana-backend/client`):

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `client/get-kaapana-instances` | Load local + remote instances (initial + 15 s poll). |
| GET | `client/check-for-remote-updates` | "sync remotes" — pull fresh state from remotes. |
| POST | `client/remote-kaapana-instance` | Register a new remote instance. |
| PUT | `client/remote-kaapana-instance` | Save edits to a remote instance. |
| PUT | `client/client-kaapana-instance` | Save edits to the local instance. |
| DELETE | `client/kaapana-instance?kaapana_instance_id=<id>` | Delete a remote instance (and its jobs). |
| POST | `client/get-dags` | DAG list for the allowed-DAGs editor (body: `instance_names`, `kind_of_dags`). |

Dataset lookup (`src/common/api.service.ts`, `loadDatasets(false)`, base
`VITE_KAAPANA_BACKEND_ENDPOINT=/kaapana-backend/`):

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `client/datasets` | Dataset options for the allowed-datasets editor (no query params on this path). |

Auth (base-ui `useAuthStore.checkAuth`, run before every route; **not**
project-prefixed):

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/oauth2/userinfo` | User identity/roles in the deployed platform. |
| GET | `/jsons/testingAuthenticationToken.json` | Dev-only fallback when the oauth2 proxy is absent. |

There is no project store in this view, so it issues **no `/aii` calls**; toasts
are client-side (`@kyvg/vue3-notification`), not HTTP.

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
cd services/base/federated-ui/docker/files
npm ci
npm run dev        # Vite dev server on http://localhost:5000
```

Standalone the app serves at `/federated-ui/`. In the platform it is reached
through the shell at `/project/<short_id>/federated-ui/`; the dev/preview
server strips the `/project/<short_id>/` prefix like traefik does (see
`vite.config.ts`), so the project-scoped URL works locally too. See
`docs/source/development_guide/preview/project_scoping.rst` for the scoping
convention.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route`.

```bash
cd services/base/federated-ui/docker/files
npx playwright test    # fixed port 4307 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing.

Suites: `runner-instances`, `add-instance`, `instance-actions`,
`project-scope`, `regressions`.
