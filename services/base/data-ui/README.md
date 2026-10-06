# data-ui

The **Data** view: a Vue 3 + Vuetify 3 + Vite single-page app on top of the
experimental [`data-api`](../data-api/README.md). It is served by nginx and
embedded by the `portal-ui` shell as a same-origin iframe under
**Experimental → Data**. It browses the data entities of the selected project,
their metadata, artifacts, storage locations and hierarchy, and offers a filter
builder over the metadata index.

The shell discovers the view through the Ingress `kaapana.ai/ui.*` annotations
(`data-ui-chart/templates/service.yaml`). The view is project-scoped through the
`/project/<short_id>/` document-URL prefix (`kaapana.ai/ui.project: "path"`, see
[Project scoping](#project-scoping)).

## `@kaapana/base-ui`

The view consumes `@kaapana/base-ui` like the other reviewed views:

| From base-ui | Used for |
|---|---|
| `createKaapanaVuetify` | Shared theme, Roboto, icon set |
| `useShellSettings` | Dark mode and the remount on shell setting changes |
| `httpClient`, `httpClientWithoutTimeout` | All `data-api` calls; the interceptor adds the project prefix. The streaming id indexes and the prune use the client without timeout |
| `getProjectBase`, `getProjectSlug` | Project prefix for URLs that bypass axios (thumbnails, downloads, previews, the websocket) and the router base |
| `ConfirmDialog` | Every destructive confirmation and the discard-changes prompts |
| `ErrorDetailsDialog`, `apiErrorInfo`, `apiErrorText` | Failure details behind notifications and inline errors |
| `postViewDirty` | Reporting unsaved metadata or schema edits to the shell |
| `kaapanaIcons` | Semantic action icons, extended by the view's own icons in `src/utils/icons.ts` |

This MR adds `data-api` to base-ui's `PROJECT_SCOPED` pattern, the only
base-ui change.

Kept local, because only this view uses them today:

- `SchemaFormRenderer.vue` renders a form from a JSON Schema. It is the
  strongest candidate for base-ui once a second view edits schema-backed data.
- The query builder (`components/queryBuilder/`) is specific to the data-api
  query model.
- `stores/failureDetails.ts`, `utils/notify.ts` and
  `composables/useFocusReturn.ts` follow the same pattern as the other views'
  local copies. Moving them to base-ui should happen for all views at once.

## Features

- **Entity gallery**: a virtualised card grid. It loads the full id index of
  the project once, then fetches records page by page as rows scroll into
  view. The `+`/`-` buttons and keys change the number of cards per row. A
  scroll indicator shows the position in long lists.
- **Live updates**: a websocket (`/data-api/v1/ws/events`) adds new entities,
  drops deleted ones, and reloads changed ones when they are visible. While a
  filter is active, it re-runs the filter instead. A filter is also re-synced
  every 30 s.
- **Filter**:
  - Conditions on `id`, `storage.type` and `metadata.<key>.<path>`, combined in
    nested all/any groups.
  - Field and value suggestions come from the registered schemas and sampled
    data of the project.
  - Filters can also be edited as JSON, and copied or pasted as JSON.
  - The filter is kept in the URL (`?q=…&qa=1`), so a filtered view can be
    shared. It can be turned off without losing it.
- **Entity detail**:
  - An overview with preview, creation time, parent, children and storage
    count.
  - **Metadata**:
    - Edit an entry in a form generated from its schema, or as JSON.
    - Required fields are validated on save.
    - Add an entry for a registered key the entity does not have yet.
    - Remove an entry, after confirmation that names the files deleted with it.
  - **Artifacts**: preview images, preview other files in a sandboxed frame,
    and download them.
  - **Storage**: the storage coordinates of the entity.
  - **Hierarchy**: navigate to the parent and children.
  - Unsaved edits are protected when the dialog is closed or another entity is
    opened, and they are reported to the shell.
- **Metadata schemas**:
  - List, view, edit, register and delete schemas. Schemas are shared by all
    projects.
  - A schema still in use cannot be deleted; the reason is shown.
  - Unsaved edits are protected.
- **Maintenance**: prune artifact files that no longer belong to any entity,
  after a confirmation that says it covers all projects.
- **Keyboard shortcuts** (`?` lists them): `F`, `C`, `P` and `X` for the
  filter, `+` and `-` for the grid. They are ignored while a text field has
  the focus or a dialog is open.

## Project scoping

- The chart declares `kaapana.ai/ui.project: "path"` and a
  `data-ui-project-ingressroute`, so the shell serves the view under
  `/project/<short_id>/data-ui/` and reloads it on a project switch.
- `data-api` gets a matching `data-api-project-ingressroute`. base-ui's
  interceptor rewrites `/data-api/…` to `/project/<short_id>/data-api/…`, and
  auth-backend adds the trusted `Project` header.
- `data-api` has no project column. It scopes by the `permissions` metadata
  entry (`{"project": <project id>, "owner": …}`) that the DICOM ingestion DAG
  attaches. With a `Project` header it:
  - lists, queries and returns only entities whose entry names that project;
  - samples field hints only from them;
  - answers 404 for other projects' entities;
  - assigns entities created through the prefix to the project;
  - refuses to move or remove the entry.
- Websocket clients on the project route only receive entity events of their
  project.
- Requests without the header stay unscoped. That covers in-cluster callers
  such as the ingestion DAG, and the unprefixed route, which OPA only opens to
  admins.
- Inside a project, the view disables "Remove entry" for the `permissions`
  entry and says why.

An entity without a `permissions` entry belongs to no project. It shows up only
through the unprefixed admin route.

## Backend endpoints

All calls go to `/data-api/v1`, prefixed with `/project/<short_id>` when the
view is served under a project.

| Method | Path | Used for |
|---|---|---|
| GET | `/entities/index/full` | Ordered id index of all entities (streamed) |
| GET | `/entities/records?limit&cursor` | Pages of full entity records |
| GET | `/entities/{id}` | One entity (detail, live updates) |
| DELETE | `/entities/{id}` | Delete an entity |
| POST | `/entities/query` | Pages of entities matching a filter |
| POST | `/entities/query/index` | Ordered ids matching a filter (streamed) |
| POST | `/entities/{id}/metadata` | Add or replace a metadata entry |
| DELETE | `/entities/{id}/metadata/{key}` | Remove a metadata entry |
| GET | `/entities/{id}/metadata/{key}/artifacts/{artifact}?disposition=` | Thumbnails, previews and downloads |
| GET | `/metadata/keys` | Registered schema keys |
| GET, POST, DELETE | `/metadata/keys/{key}` | Read, register or replace, and delete a schema |
| GET | `/metadata/keys/{key}/fields` | Field hints for the filter |
| GET | `/metadata/keys/{key}/field-values?path` | Value suggestions for the filter |
| POST | `/artifacts/prune` | Delete orphaned artifact files |
| WS | `/ws/events` | Live entity and schema events |

### Known limitations

- **Live updates across workers**: `data-api` runs 4 uvicorn workers, and its
  event bus lives in each worker's memory. A websocket client only receives
  events of changes handled by its own worker. The view makes up for it by
  re-syncing an active filter every 30 s and reloading entities when they come
  back into view. A fix needs a shared channel, such as Postgres
  `LISTEN/NOTIFY`, and belongs in a follow-up issue.
- **Admin only**: OPA allows `/data-ui` and `/data-api` only for the `admin`
  role, as before this MR. Opening the view to project members is a separate
  decision.
- **Schemas and pruning are global**: metadata schemas are shared by all
  projects, and pruning covers the artifact storage of all projects. The UI
  says so in both places.
- **Single-key shortcuts**: WCAG 2.2 (2.1.4) asks that character-key shortcuts
  can be turned off or remapped. The shortcuts are inactive while a text field
  has the focus or a dialog is open, but cannot be turned off yet.

## Development

`@kaapana/base-ui` is a `file:` dependency consumed as its built `dist/`, so
build the library first (and again after any change to its `src/`):

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build
```

Then run the view from its `docker/files`:

```bash
cd services/base/data-ui/docker/files
npm ci
npm run dev            # Vite dev server on http://localhost:5173/data-ui/
```

The dev server proxies `/data-api` to `http://localhost:8080`, where
`services/base/data-api/compose.yaml` starts the API with a Postgres. Without
a running API, use the e2e mocks below. Production serves the static `dist/`
from the unprivileged nginx image on port `5000` (`nginx.conf`). The image is
built on the `local-only/base-ui:latest` base stage (see `docker/Dockerfile`).

**In-cluster dev loop:**

1. Run `npm ci` in `docker/files` on the host.
2. Switch the `Dockerfile` to its development part.
3. Set `global.dev_files` in `data-ui-chart/values.yaml` to the host path of
   `docker/files`, and deploy.

The chart then mounts the sources into the container and serves Vite with hot
module reload on port `5173`.

Lint and formatting use the repository-wide ESLint/Prettier toolchain, so the
app carries no lint scripts of its own:

```bash
ci/ci-code/lint/ui_lint.sh services/base/data-ui/docker/files/src/**/*.{ts,vue}
```

## Tests

A mock-backed Playwright suite in `docker/files/tests/e2e` covers the view
without a platform. `fixtures/mock-backend.ts` serves an in-memory `data-api`,
including filter evaluation, schema registration, the 409 for a schema in use,
and a mocked websocket. Requests are recorded so that specs can assert payloads
and the project prefix.

| Spec | Covers |
|---|---|
| `boot.spec.ts` | Listing; project prefix on requests, thumbnails and the websocket; unprefixed standalone mode; live create and delete |
| `states.spec.ts` | Empty project, could-not-load with details and retry, no-match with filter off, failed page load |
| `filter.spec.ts` | Building a condition, URL deep link, turning the filter off and on, JSON mode and its validation, rejected filters |
| `entity-detail.spec.ts` | Tabs and hierarchy navigation; saving with artifacts kept; required-field validation; unsaved-changes protection and `postViewDirty`; adding and removing entries; the protected `permissions` entry; failure details |
| `delete.spec.ts` | Confirmation with the safe action focused, focus return, deleting from the dialog, failed deletion |
| `schemas.spec.ts` | Registering (previously broken), key and JSON validation, delete in use and unused, unsaved edits, opening from an entry |
| `maintenance.spec.ts` | Confirmed prune and its result, cancelled prune |
| `guidelines.spec.ts` | Theme, typeface, shell dark mode, primary actions, dialog widths, accessible names, focus handling, shortcuts |

```bash
cd services/base/data-ui/docker/files
npx playwright test               # local: against the dev server on port 4312
npm run build && CI=1 npx playwright test   # as in CI: against the production preview
```

CI runs the suite in the `ui_e2e_tests` matrix (`ci/pipeline/unit-tests.yml`).
The project scoping of `data-api` is covered by the Postgres-backed
`data_api_tests` job (`services/base/data-api/docker/tests`).

## Relationship to `data-gallery-ui` and leaving Experimental (proposal)

This section is a proposal to agree with the Kaapana leads.

- **Today**:
  - `data-gallery-ui` (**Datasets**) is the production data view. It is built
    on the OpenSearch series index of `kaapana-backend`: DICOM series,
    datasets, workflow start and the OHIF viewer.
  - `data-ui` is the view on the new, type-agnostic `data-api` layer. It
    covers entities of any kind, schema-backed metadata, artifacts, storage
    locations and hierarchy.
  - Both show DICOM series, because the ingestion DAG registers series in
    both stores.
- **Ownership**:
  - Until the data-api v2 roadmap (datasets, Storage API, workflow
    integration) lands, `data-gallery-ui` owns finding series, curating
    datasets and starting workflows.
  - `data-ui` owns inspecting and editing data-api entities, their metadata
    and schemas.
  - `data-ui` should not add dataset or workflow features of its own. They
    should come with the data-api concepts behind them.
- **Leaving Experimental**: `data-ui` can move to the Data section once all of
  the following hold:
  1. data-api has a proper project model (a column or table, not a metadata
     convention) and serves project members, not only admins.
  2. Live updates work across workers.
  3. Datasets exist as data-api concepts, so `data-gallery-ui`'s dataset
     features can move or be reimplemented on data-api.

  From then on, `data-gallery-ui` becomes a client of data-api, or is merged
  into `data-ui`.
