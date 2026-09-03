# data-gallery-ui

The **Datasets** view — one of the Kaapana view apps (Vue 3 + Vuetify 3 + Vite
SPA, served by nginx and embedded as a same-origin iframe by the `portal-ui`
shell). It browses the DICOM series index as a
thumbnail gallery with metadata search/filters, manages datasets (named series
collections), shows a per-series detail pane with the OHIF viewer and a
statistics dashboard, and triggers workflows on the current selection.

Like the other views it is discovered by the shell through its Ingress
`kaapana.ai/ui.*` annotations and is project-scoped by the
`/project/<short_id>/` document-URL prefix (see
`docs/source/development_guide/preview/project_scoping.rst` for the scoping
convention).

## Features

- **Series gallery** with a flat mode (`Gallery` → `SeriesCard`) and a
  **structured** mode grouping series by patient → study
  (`StructuredGallery` → `PatientView`/`StudyView`); the mode is a persisted
  setting (`localStorage["settings"]`).
- **Search & filters** (`Search.vue`): free-text query plus add/remove field
  filters whose selectable values (with counts) are fetched per field; a
  selected dataset scopes the query to its identifiers.
- **Pagination** (`Paginate.vue`) driven by the aggregated series count, with
  an optional sliced-search mode.
- **Rubber-band + click selection** of series (`selecto`/`keycon`), with the
  selection shared app-wide via the `datasets` Pinia store.
- **Dataset management**: select a dataset from the sidebar; Save-as, Add-to,
  Remove-from, and an Edit-datasets dialog (rename/delete); download the
  selection as a zip.
- **Tagging** (`TagBar`, `TagChip`, `TagsTable`, `SeriesCard`): filter by tag
  and add/remove tags on individual series.
- **Detail pane** (`DetailView`): series metadata table plus the **OHIF
  viewer** embedded via `IFrameWindow` (loaded under the project's `/ohif`
  prefix), with an open-in-new-tab button.
- **Dashboard** (`Dashboard.vue`, ApexCharts): histograms/metrics over the
  current result set; clicking a bar feeds a filter back into the search.
- **Workflow execution**: the shared `WorkflowExecution` dialog from
  `@kaapana/base-ui/workflow-execution` runs a dataset-kind DAG over the
  selected series (`onlyLocal`, `kind_of_dags="dataset"`).
- **DICOM validation reports**: view/re-run/delete/download a series'
  validation report (re-run/delete go through the workflow dialog with a fixed
  DAG).
- **Deep links** via `?project_name=` / `?dataset_name=` query params, which
  can move the document under another project's prefix.

## Design guidelines

The view follows the Kaapana frontend design guidelines
(`services/base/base-ui/docker/files/kaapana-design-guidelines-draft.md`). The
parts that shape the code rather than only its styling:

| Guideline | Where it lives |
| --- | --- |
| Visual language | `src/plugins/vuetify.ts` builds Vuetify through `createKaapanaVuetify`, so the theme, the MDI icon set and the platform typeface (Roboto) all arrive together. `App.vue` sets no font or text colour of its own. |
| Icons | `src/utils/galleryIcons.ts` re-exports the shared `kaapanaIcons` map and names this view's own domain symbols. No `mdi-*` string at a call site. |
| Action hierarchy | Toolbar and table actions are tertiary (`variant="text"`); the main action of a task area is `color="primary" variant="flat"`; destructive actions are `color="error"`. |
| Confirmations | `src/components/ConfirmDialog.vue` — title plus consequences, `tone="destructive"` (error) or `tone="high-impact"` (primary), initial focus on the safe action, Escape and outside clicks cancel. Used for removing series from a dataset, deleting a dataset, discarding an edited dialog, and starting a download. |
| Unavailable actions | Disabled controls carry a tooltip *and* an accessible name that states the precondition, not just the action. |
| Validation | `SaveDatasetDialog.vue` validates on blur and on submit, and its messages say what to enter and how to fix it. |
| Unsaved changes | `Search.vue` and `SaveDatasetDialog.vue` each report their own dirty state upward; `Datasets.vue` posts the **combined** state once via `postViewDirty`, so the parts cannot overwrite each other. Closing an edited dialog is guarded. |
| Loading | Mutation progress shows on the control that started it, and a running mutation cannot be submitted twice. The gallery skeleton mirrors the card grid it replaces. |
| Errors | `src/utils/errors.ts` turns a rejection into "what failed" plus the backend's actionable `detail`, never a bare status code or an interpolated `Error`. |
| Empty states | `src/components/GalleryEmptyState.vue` distinguishes "nothing exists yet", "nothing matches" and "could not load", each with its own next step. A failed load is never shown as an empty collection. |
| Accessibility | Every icon-only control is a real `<v-btn>` with an `aria-label` — handlers used to sit on the `<v-icon>` inside, which no keyboard could reach. Tag chips derive a foreground colour by luminance (`src/utils/tagColors.ts`) instead of inheriting one. |

## Backend endpoints

All calls go through the shared `httpClient` (axios) in `@kaapana/base-ui`.
Its request interceptor rewrites URLs matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` onto the
document's `/project/<short_id>` prefix. So **every `/kaapana-backend/*` call
below is project-scoped**; the `/aii/*`, `/oauth2/*`, and `/jsons/*` calls are
**not**.

Dataset CRUD — `src/common/api.service.ts` (`/kaapana-backend/client/*`, scoped):

| Method + path | Purpose |
| --- | --- |
| `GET client/datasets?skip_identifiers=true` | list datasets for the sidebar selector |
| `GET client/dataset?name=&access_level=` | load one dataset by name (Search) |
| `POST client/dataset` | create a dataset from the selection (Save-as dialog) |
| `PUT client/dataset` | add / remove / update dataset members |
| `DELETE client/dataset?name=` | delete a dataset (Edit-datasets dialog) |

Series & metadata queries — `src/common/api.service.ts` (`/kaapana-backend/dataset/*`, scoped):

| Method + path | Purpose |
| --- | --- |
| `POST dataset/series` | gallery listing — flat UID list or structured patient tree |
| `GET dataset/series/{uid}` | one series' metadata + thumbnail (DetailView, SeriesCard) |
| `POST dataset/aggregatedSeriesNum` | count of series matching the query (pagination) |
| `GET dataset/search_fields` | searchable fields + max clause count |
| `GET dataset/field_names` | filterable field names |
| `POST dataset/query_values/{key}` | distinct values (+counts) for a field / for `Tags` |
| `POST dataset/tag` | add / remove tags on series |
| `POST dataset/dashboard` | histograms + metrics for the current set |
| `GET dataset/download?series_uids=` | zip of selected series (blob, no timeout) |

Validation reports — `src/views/Datasets.vue` via `kaapanaApiService.kaapanaApiGet` (scoped):

| Method + path | Purpose |
| --- | --- |
| `GET get-static-website-result-reports?series_id=` | resolve a series' validation-report HTML URL |

Auth — `@kaapana/base-ui` `authService` (**not** scoped):

| Method + path | Purpose |
| --- | --- |
| `GET /oauth2/userinfo` (prod build) / `GET /jsons/testingAuthenticationToken.json` (dev) | current-user JWT |

`AuthService.logout()` navigates (`location.href`) to `/kaapana-backend/oidc-logout` — a page navigation, not an intercepted API call.

Project scoping — `@kaapana/base-ui` project store + `fetchProjects` in `api.service.ts` (`/aii/*`, **not** scoped):

| Method + path | Purpose |
| --- | --- |
| `GET /aii/users/current` | current AII user (id + realm roles) |
| `GET /aii/projects` (admin) / `GET /aii/users/{id}/projects` (non-admin) | projects for the selector / deep-link resolution |

Workflow dialog — `@kaapana/base-ui/workflow-execution`, via `federatedClientApiPost` → `/kaapana-backend/client/*` (scoped):

| Method + path | Purpose |
| --- | --- |
| `POST client/get-kaapana-instances` | instances available as workflow targets |
| `POST client/get-dags` | DAGs runnable on a dataset |
| `POST client/get-ui-form-schemas` | VJSF form schema for the chosen DAG |
| `POST client/workflow` | submit the workflow over the selected series |
| `GET {backend-route}` (only if a form declares one) | browse a form-declared data source |

OHIF viewer — `src/components/DetailView.vue`: an iframe `src` / `window.open`
target built as `${getProjectBase()}/ohif/viewer?StudyInstanceUIDs=…&mode=iframe`.
Path-scoped through the document prefix, but a browser navigation, not an
`httpClient` call.

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
cd services/base/data-gallery-ui/docker/files
npm ci
npm run dev            # Vite dev server on http://localhost:5000
```

In the platform the view is reached through the shell at
`/project/<short_id>/data-gallery-ui/`. The dev/preview server strips the
`/project/<short_id>/` prefix like traefik does (see `vite.config.ts`), so the
project-scoped URL works locally too; served without the prefix, the project
store redirects onto the user's first project.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route`.

`guidelines.spec.ts` covers the design-guidelines behaviour listed above —
accessible names, keyboard operability, what a confirmation says and which
button it focuses, the three empty states, validation wording, the combined
dirty state, and error text. It asserts behaviour a user can observe, not
styling, which the shared theme owns.

```bash
cd services/base/data-gallery-ui/docker/files
npx playwright test    # fixed port 4304 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing. There is no unit-test script.
