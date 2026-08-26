# workflow-execution-ui

The standalone **Workflow Execution** view — one of the Kaapana view apps (Vue
3 + Vuetify 3 + Vite SPA, served by nginx and embedded as an iframe by the
`portal-ui` shell, discovered via `kaapana.ai/ui.*` Ingress annotations, and
project-scoped through the `/project/<short_id>/` document-URL prefix). It is a
thin wrapper (`src/views/WorkflowExecution.vue`) around the shared generic
`WorkflowExecution` component from `@kaapana/base-ui/workflow-execution`: the
wrapper only lays the component out and, on a successful submit, hands off to
the shell's workflow list (`navigateShell('/web/workflows/workflows')`, i.e. a
postMessage to the shell when embedded and a top-window navigation standalone).

Because the shared component ships no e2e of its own (only Storybook stories in
`base-ui`), **this app's Playwright suite is the primary regression net for it** —
the other two embeds (`data-upload-ui`, `data-gallery-ui`, which mount it as a
dialog) rely on the coverage here.

## Features

Driven by the wrapper + the shared component + the backend-supplied per-DAG
schemas:

- **Runner-instance selection** — a single local instance is auto-selected and
  its multi-select stays hidden; the "Runner instances" select renders only when
  more than one instance is available.
- **DAG selection** — a type-to-filter `v-autocomplete` ("Workflow"); a project
  with a single DAG auto-selects it on boot. `kind_of_dags` / `validDags` props
  narrow the list.
- **Workflow name** — auto-filled from the DAG id, editable, required.
- **Schema-driven forms** — each DAG's `get-ui-form-schemas` response is rendered
  with vjsf 3 (`workflow_form`, `data_form`, optional `external_schemas`);
  `documentation_form` renders as a docs link instead of a form; `backend_form`
  renders a `v-treeview` file/folder picker fed by a dynamic backend route.
- **vjsf 2→3 bridging** — the backend still emits vjsf-2-dialect schemas.
  `normalizeV2Schema` + `@koumoul/vjsf/compat/v2` adapt them before render:
  boolean `required: true` on a property → parent-level `required: []` array;
  value-discriminated `dependencies`/`oneOf` → `allOf`/`if`/`then`; empty
  `enum`/`oneOf` stripped and marked `readOnly` (so "nothing to pick yet" fields
  show their notice instead of blanking the form); object-const `oneOf` node
  types reconciled. Field `description`s surface via vjsf's own muted `(i)` help
  toggle.
- **Settings-based defaults + `hideOnUI`** — `localStorage["settings"].workflows`
  (shell-seeded, keyed by `camelCase(dag_id)`) overrides schema defaults per
  field; fields listed under `hideOnUI` are marked `x-display: hidden` (not
  rendered, but their default still reaches the submitted payload).
- **Native dataset picker + limit** — `dataset_name` and `dataset_limit` are
  lifted out of vjsf into native Vuetify controls: a virtualized, searchable
  autocomplete (survives thousands of datasets, where the vjsf `oneOf` overflows
  the render stack) and a "Process whole dataset" toggle + min-1 number input.
  The dataset object-const is serialized to a scalar for the picker and restored
  into `data_form` on submit; the limit is omitted when "whole dataset" is on.
- **Validation gating** — required-field checks, and any boolean field literally
  named `confirmation` must be `true` before submit fires.
- **Unsaved-changes (view-dirty) reporting** — the view posts
  `kaapana:view-dirty` to the shell (`postViewDirty`) so a project switch (which
  reloads the iframe and discards in-memory form state) can warn first. On by
  default for the standalone view (`!isDialog`). The DAG choice counts as dirty
  only in a multi-DAG project (a single-DAG project re-selects on reload); form
  edits are diffed against a baseline that absorbs vjsf's async default
  population until the user first interacts.
- **Success redirect** — on submit the shared component resets and emits
  `successful`; the wrapper calls `navigateShell('/web/workflows/workflows')`.
  Embedded that posts `kaapana:navigate` to the shell and deliberately leaves
  the top window alone (the shell swaps the iframe without reloading itself);
  standalone there is no shell to ask, so it navigates the top window.

## Backend endpoints

All runtime calls go through `@kaapana/base-ui` `kaapanaApiService` / `httpClient`.
Calls matching `^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/`
are **rewritten to `/project/<short_id>/…` by the shared httpClient interceptor**
(marked *scoped* below); the `<short_id>` comes from the document URL. **There is
no project store in this app** — the URL prefix is the only project input.

| Method | Path | Purpose | Scoped |
| --- | --- | --- | --- |
| POST | `/kaapana-backend/client/get-kaapana-instances` (bare) | list runner instances at boot / on refresh | yes |
| POST | `/kaapana-backend/client/get-kaapana-instances` `{dag_id}` | remote instances allowing an external DAG — **remote/federated branch only** (schema carries `external_schemas`) | yes |
| POST | `/kaapana-backend/client/get-dags` `{instance_names, kind_of_dags}` | available DAGs for the selected instances | yes |
| POST | `/kaapana-backend/client/get-ui-form-schemas` `{workflow_name, instance_names}` | per-DAG form schemas | yes |
| POST | `/kaapana-backend/client/get-ui-form-schemas` `{workflow_name, dag_id, instance_names}` | external-DAG form schemas — **remote/federated branch only** | yes |
| POST | `/kaapana-backend/client/workflow` `{workflow_name, dag_id, instance_names, conf_data, remote, federated}` | submit the workflow | yes |
| GET | `/kaapana-backend<backend-route>[?prefix=<path>]` | `backend_form` file-tree root + lazy children (route comes from the schema) | yes |
| GET | `/oauth2/userinfo` (prod) · `/jsons/testingAuthenticationToken.json` (dev fallback) | auth check, via `base-ui` `authService` / auth store | **no** (goes through the same client but doesn't match the scope regex) |

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
cd services/base/workflow-execution-ui/docker/files
npm ci
npm run dev            # Vite dev server on http://localhost:5000 (strictPort)
```

Standalone the app is served under its Vite `base`,
`http://localhost:5000/workflow-execution-ui/`. In the platform the view is
reached through the shell at `/project/<short_id>/workflow-execution-ui/`; the
dev/preview server strips the `/project/<short_id>/` prefix like traefik does
(see `vite.config.ts`), so the project-scoped URL works locally too.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route`.

```bash
cd services/base/workflow-execution-ui/docker/files
npx playwright test    # fixed port 4308 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` — **including the shared `WorkflowExecution`
component this app wraps** — before running tests; consumers otherwise import
the stale `dist/` through the npm symlink and nothing errors, the change is
just missing.

Suites: `flow`, `submit-validation`, `vjsf-defaults`, `vjsf-fields`,
`view-dirty`, `realistic-dags`, `project-scope`.

See `docs/source/development_guide/preview/project_scoping.rst` for the scoping
convention.
