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

- **Instance overview** (`views/RunnerInstances.vue`) — a page title with a
  summary line, then two sections: **This platform** (the local instance) and
  **Remote instances**. Cards sit in a two-column grid inside a 1600 px
  readable width. The list refetches on a 15 s poll; a mutation that lands
  while a fetch runs queues one more fetch instead of being dropped.
- **States** — skeleton cards on the first load; a failed first load shows an
  error empty state with *Try again* and *Details*; a failed poll keeps the last
  list under a warning alert; no remotes shows an empty state that points to
  the *Add remote instance* button in the page header.
- **Instance card** (`components/InstanceCard.vue`, rows in
  `components/InstanceField.vue`) — name, local/remote subtitle and, for a
  remote, an *Updated …* chip (success < 5 min, warning < 5 h, error older,
  neutral *Never updated* for a remote that has not reported yet). Values are
  stated in text (*Yes*/*No*, *Deactivated*, *None*), not by colour alone.
- **Edit in place** — one field at a time per card: pencil → field with Save and
  Cancel; Enter saves. Remote cards edit network port, token, Fernet key, SSL
  verification and sync timeout; the local card edits Fernet encryption, SSL verification,
  automatic sync, automatic workflow start, allowed workflows and allowed
  datasets. Invalid values disable Save and say how to fix them. A failed save
  keeps the field open with the entered value. A background poll never
  overwrites a field being edited.
- **Add remote instance** (`components/AddRemoteInstance.vue`) — a medium
  dialog with *Enter details* and *Paste details* tabs (both `eager`, so
  validation also runs when submitting from the paste tab). Pasted JSON fills
  the fields; invalid JSON is explained under the field. A rejected request is
  shown as an inline alert with *Details*; the button is busy while the request
  runs. Closing with entered details asks before discarding them.
- **Delete remote** — `ConfirmDialog` (error colour, Cancel focused) stating
  that the jobs held for that instance are deleted and the remote platform is
  not changed.
- **Copy connection details** — copies the local instance definition as JSON,
  in exactly the shape the *Paste details* tab reads.
- **Sync remote instances** — triggers a remote-update check, confirms, and
  refetches; disabled while there is no remote. The backend contacts all
  remotes concurrently and waits for each at most its *sync timeout* (per
  remote, 1–300 s, default 15 s), then answers 502 naming each one that failed
  (timeout, connection error or any non-200 status); the view reports that and
  still refetches the remotes that synced.
- **Feedback** — successes are transient notifications; failures are error
  notifications whose technical detail opens in `ErrorDetailsDialog` when
  selected (`utils/notifyFailure.ts`, `stores/failureDetails.ts`).
- **Unsaved changes** — an edited field or a filled add dialog is reported to
  the shell with `postViewDirty` (`composables/viewDirty.ts`).
- Allowed-workflow and allowed-dataset options are fetched only when their
  editor opens; datasets are limited to `access_level === 'project'`.

## Backend endpoints

Every call goes through `src/api/federation.ts`, which wraps
`kaapanaApiService.federatedClientApi*` from `@kaapana/base-ui` and owns the
request/response types the e2e fixtures import. The shared `httpClient`
rewrites `/kaapana-backend/…` onto the `/project/<short_id>` document prefix,
so **all calls below are project-scoped**; the auth calls are not.

Federation client API (base path `/kaapana-backend/client`):

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `get-kaapana-instances` | Load local + remote instances (initial + 15 s poll). |
| GET | `check-for-remote-updates` | *Sync remote instances*; 502 lists the remotes that failed. |
| POST | `remote-kaapana-instance` | Register a new remote instance. |
| PUT | `remote-kaapana-instance` | Save port, token, Fernet key, SSL check or sync timeout of a remote. |
| PUT | `client-kaapana-instance` | Save the local instance settings. |
| DELETE | `kaapana-instance?kaapana_instance_id=<id>` | Delete a remote instance, the jobs sent to it and the workflows received from it. |
| POST | `get-dags` | Workflow options for the allowed-workflows editor. |
| GET | `datasets?skip_identifiers=true` | Dataset options for the allowed-datasets editor. |

These endpoints belong to the legacy `kaapana-backend`. They are the only
implementation of federation, and no successor API exists yet, so the view
keeps using them.

Auth (base-ui `useAuthStore.checkAuth`, run before every route; **not**
project-prefixed):

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/oauth2/userinfo` | User identity/roles in the deployed platform. |
| GET | `/jsons/testingAuthenticationToken.json` | Dev-only fallback when the oauth2 proxy is absent. |

There is no project store in this view, so it issues **no `/aii` calls**.

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
`project-scope`, `regressions`, and `guidelines` (the cross-cutting rules of
the Kaapana design guidelines: confirmation focus and colour, typeface, readable
width, one primary action, shared icons, accessible names).
