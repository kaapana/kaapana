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

The whole app lives under `docker/files/`; the single view is
`src/views/Datasets.vue`. The parts it is built from:

| Path | Purpose |
| --- | --- |
| `src/components/Search.vue` | Free-text search, field filters, the deep-link parameters, and the dataset the search is scoped to. |
| `src/components/Gallery.vue`, `SeriesCard.vue`, `StructuredGallery.vue`, `PatientView.vue`, `StudyView.vue` | The flat and the patient/study-grouped gallery. |
| `src/components/GalleryEmptyState.vue` | Why the gallery is empty (nothing yet / nothing matches / dataset empty / could not load), on `v-empty-state`. |
| `src/components/TagBar.vue`, `TagChip.vue`, `Chip.vue` | Tag list, tagging by card click, tag chips. |
| `src/components/DetailView.vue`, `TagsTable.vue`, `IFrameWindow.vue` | The detail pane: OHIF viewer and metadata table, from one metadata request. |
| `src/components/Dashboard.vue` | Metrics and histograms of the current selection. |
| `src/components/SaveDatasetDialog.vue`, `AddToDatasetDialog.vue`, `EditDatasetsDialog.vue` | Save a selection as a dataset, add to one, manage (list and delete) datasets. |
| `src/components/DownloadDatasetBtn.vue` | Download of the selection, with its confirmation. |
| `src/components/ValidationReportDialog.vue`, `ElementsFromHTML.vue` | A series' DICOM validation report. |
| `src/composables/useFocusReturn.ts` | Returns focus to the control that opened a dialog. |
| `src/utils/notifyFailure.ts`, `src/stores/failureDetails.ts` | A failed action as a notification whose details open in `ErrorDetailsDialog` (same code as extensions-ui). |
| `src/utils/datasets.ts` | How a dataset is labelled and told apart (name and access level), and what a dataset list says when it shows no entry. |
| `src/utils/tagColors.ts` | A tag's chip colour, hashed from its name, with a foreground picked for contrast. |

The theme, typeface, icon map, `ConfirmDialog`, `ErrorDetailsDialog`, the api
error helpers and the workflow dialog come from `@kaapana/base-ui`; icons
specific to this view live in `src/utils/galleryIcons.ts`.

## Features

- **Series gallery** with a flat mode (`Gallery` → `SeriesCard`) and a
  **structured** mode grouping series by patient → study
  (`StructuredGallery` → `PatientView`/`StudyView`); the mode is a persisted
  setting (`localStorage["settings"]`).
- **Search & filters** (`Search.vue`): free-text query plus add/remove field
  filters whose selectable values (with counts) are fetched per field; a
  selected dataset scopes the query to its identifiers, and an empty dataset
  scopes it to nothing.
- **Pagination** (`Paginate.vue`) driven by the aggregated series count, with
  an optional sliced-search mode.
- **Rubber-band and click selection** of series (`selecto`), with the
  selection shared app-wide via the `datasets` Pinia store.
- **Datasets**: pick one in the selector at the top of the main pane; Save as
  dataset, Add to dataset, Remove from dataset, and a Manage-datasets dialog
  that lists and deletes datasets; download the selection as a zip.
- **Tagging** (`TagBar`, `TagChip`, `TagsTable`, `SeriesCard`): pick tags in the
  tag bar, then click a series card to add or remove them; remove a tag from a
  card with its chip.
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
- **Deep links** via `?project_name=`, `?dataset_name=` (with `access_level=`),
  `?query_string=` and field filters, e.g. `?dataset_name=nsclc&Modality=CT`;
  the copy-link button writes one. A link to another project moves the
  document under that project's prefix. A link is applied once and then
  leaves the address, so a remount does not apply it again.

## Design guidelines

The view follows the Kaapana frontend design guidelines
(`docs/source/development_guide/preview/design_guidelines.rst`). What shapes
the code, and the tests that hold it (`spec › test`):

| Guideline | In this view | Tested by |
| --- | --- | --- |
| Be consistent | Confirmations use base-ui `ConfirmDialog`, failure details `ErrorDetailsDialog`, empty states `v-empty-state`; no app-local component defaults. | `confirmations` (all), `feedback › the details dialog holds the request line…`, `guidelines › icon buttons keep the round shape…` |
| Typography, Color | `createKaapanaVuetify` brings theme and typeface; tag chips take `tagColors.ts` with a luminance-picked foreground; chart labels take the theme's `on-primary`. | `guidelines › the view uses the platform typeface…`, `regressions › tag bar chips are colored…`, `dashboard › the numbers on the bars take the theme foreground…` |
| Icons | `galleryIcons.ts` re-exports `kaapanaIcons` and names this view's own symbols; re-running a validation is `restart`. | `validation-report › re-running the validation uses the restart symbol` |
| Action hierarchy | The Search button is the one filled primary action; toolbar actions are text buttons, Remove `error`, Start workflow `primary`; empty states offer text actions. | `guidelines › the "…" empty state offers its next step as a text action` (4), `regressions › dataset action icon buttons are flat…` |
| Unavailable actions | Disabled toolbar and tag-bar buttons say why in their tooltip and accessible name; while disabled, their wrapper is the tab stop, so the reason is reachable by keyboard. | `guidelines › a disabled action explains why…`, `› Tab reaches an unavailable action…`, `› an unavailable action is one tab stop…`, `› the tag list cannot be saved empty…` |
| Confirmations | Remove, delete dataset, discard and download confirm with a short title, a text naming what is affected and what follows, Cancel focused, `error` (destructive) or `primary` (download); the download states the 256 MB limit. | `confirmations › <each> › says what it affects…`, `› Escape cancels without a request…`, `› the download confirmation states the size limit` |
| Dialogs | Confirmations 400 px, forms 600 px, the datasets table and the report 900 px (the 900 px ones have no test); focus moves in, and returns to the opener on close (`useFocusReturn`, base `ConfirmDialog`), also after "Discard" and after a workflow started from the validation report. | `confirmations › … says what it affects…` (400 px), `› "Keep editing" returns to the name…` (600 px), `guidelines › closing "<dialog>" with Escape returns focus…` (5), `› discarding an edited "Save selection as dataset" returns focus…`, `› closing a workflow started from the validation report returns focus…` |
| Choosing inputs | The dataset selector and the Add-to-dataset list are searchable autocompletes. | `datasets › Add to Dataset searches its datasets as the user types` |
| Validation | The dataset name is checked on blur and on submit; a name is taken per access level; Enter submits. | `guidelines › validation says what is required…`, `datasets › Enter in the name field saves, once` |
| Unsaved changes | Search and the Save dialog report their dirty state; `Datasets.vue` posts the combined state and posts clean when it unmounts; closing an edited dialog asks first. | `view-dirty` (all), `guidelines › closing an edited dialog asks before discarding…`, `› unsaved work in a dialog…`, `datasets › changing only the access level is unsaved work` |
| Loading | Skeleton for the gallery; table loading states; progress on the control that started a mutation, which runs once and does not ask again while it runs; Manage datasets stays open while a delete runs; the dataset selector shows progress while a selected dataset loads, and Remove waits for it; the Search button spins only for a search started there; the dashboard keeps its charts while reloading. | `regressions › series loading shows the skeleton animation`, `confirmations › while the confirmed action runs` (3), `datasets › saving a new dataset runs once…`, `› adding to a dataset runs once…`, `› a selected dataset shows its progress, and Remove waits…`, `search › … the Search button…` (5), `dashboard › the charts stay while the statistics reload` |
| Errors | A failed action is one notification in the user's terms; selecting it opens the backend message, status and request line; a download that gets no response or exceeds the limit says so. | `feedback` (all), `guidelines › a failed mutation is reported in words…`, `search › copying the query link says so…` (2) |
| Notifications and alerts | A load failure is reported once: inline where the page has a place for it (gallery, search row, dashboard, detail pane, lists, cards), otherwise as one notification. When the searchable fields fail, the search runs with the filters only, and the search row says the free text was left out until a search no longer needs them. | `errors` (all), `detail › a failed metadata load is one inline message…`, `validation-report › a failed lookup is a failure…` |
| Empty states | The gallery tells nothing yet, nothing matches, dataset empty and could not load apart; so do Manage datasets, the dataset lists, the metadata table and the validation report. The detail pane says when a series names no study to show; the search row's Field and Values lists say why they are empty. | `boot › shows the "nothing yet" empty state…`, `guidelines › an empty result after filtering…`, `datasets › an empty dataset shows no series…`, `› Manage datasets tells…` (2), `› the dataset selector…` (2), `detail › while the metadata loads…`, `› a series whose metadata names no study…`, `search › the Field and Values lists say why they are empty` (3) |
| Accessibility | Every icon-only control has an `aria-label`; selected tag chips are toggle buttons that carry a check and `aria-pressed`. Series cards are selected by mouse only (open point below). | `guidelines › every icon-only control…has an accessible name`, `› the dataset actions are real buttons…by keyboard`, `tags › a selected tag chip is marked and announced…` |

## Backend endpoints

All calls go through the shared `httpClient` (axios) in `@kaapana/base-ui`.
Its request interceptor rewrites URLs matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` onto the
document's `/project/<short_id>` prefix. So **every `/kaapana-backend/*` call
below is project-scoped**; the `/aii/*`, `/oauth2/*`, and `/jsons/*` calls are
**not**. The api calls report nothing themselves: a failure is thrown, and the
caller reports it once (see Design guidelines, Notifications).

Dataset CRUD — `src/common/api.service.ts` (`/kaapana-backend/client/*`, scoped):

| Method + path | Purpose |
| --- | --- |
| `GET client/datasets?skip_identifiers=true` | list datasets for the selector (identifiers left out) |
| `GET client/datasets` | list datasets with their identifiers (Manage datasets, for the sizes) |
| `GET client/dataset?name=&access_level=` | load one dataset with its identifiers (Search) |
| `POST client/dataset` | create a dataset from the selection (Save dialog) |
| `PUT client/dataset` | add / remove members (`action` `ADD` / `DELETE`) |
| `DELETE client/dataset?name=&access_level=` | delete a dataset; without the level the backend assumes `project` |

Series & metadata queries — `src/common/api.service.ts` (`/kaapana-backend/dataset/*`, scoped):

| Method + path | Purpose |
| --- | --- |
| `POST dataset/series` | gallery listing — flat UID list or structured patient tree |
| `GET dataset/series/{uid}` | one series' metadata + thumbnail URL (DetailView, SeriesCard) |
| `GET dataset/series/{uid}/thumbnail` | the thumbnail, as an `<img src>` the backend builds with the project prefix |
| `POST dataset/aggregatedSeriesNum` | count of series matching the query (pagination) |
| `GET dataset/search_fields` | searchable fields + max clause count |
| `GET dataset/field_names` | filterable field names |
| `POST dataset/query_values/{key}` | distinct values (+counts) for a field / for `Tags` |
| `POST dataset/tag` | add / remove tags on series |
| `POST dataset/dashboard` | histograms + metrics for the current set (also the structured-mode headers) |
| `GET dataset/download?series_uids=` | zip of selected series (blob, no timeout; at most 20 series, 256 MB) |

Validation reports — `src/components/ValidationReportDialog.vue` via `kaapanaApiService.kaapanaApiGet` (scoped):

| Method + path | Purpose |
| --- | --- |
| `GET get-static-website-result-reports?series_id=` | resolve a series' validation-report HTML URL |
| `GET <that URL>` | the report HTML (`ElementsFromHTML`, `httpClient`) |

Auth — `@kaapana/base-ui` `authService` (**not** scoped):

| Method + path | Purpose |
| --- | --- |
| `GET /oauth2/userinfo` (prod build) / `GET /jsons/testingAuthenticationToken.json` (dev) | current-user JWT |

`AuthService.logout()` navigates (`location.href`) to `/kaapana-backend/oidc-logout` — a page navigation, not an intercepted API call.

Project scoping — `@kaapana/base-ui` project store (`/aii/*`, **not** scoped):

| Method + path | Purpose |
| --- | --- |
| `GET /aii/users/current` | current AII user (id + realm roles) |
| `GET /aii/projects` (admin) / `GET /aii/users/{id}/projects` (non-admin) | the user's projects: resolves the URL slug, and a `?project_name=` link |

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

### Legacy API

Every data call above goes to the legacy `kaapana-backend`. None of them has a
replacement on `develop`, so all are **kept**:

| Route (kaapana-backend) | Status |
| --- | --- |
| `client/datasets`, `client/dataset` (GET, POST, PUT, DELETE) | kept: no replacement on develop for dataset CRUD |
| `dataset/series`, `dataset/aggregatedSeriesNum`, `dataset/search_fields`, `dataset/field_names`, `dataset/query_values/{key}` | kept: no replacement on develop; `data-api` `POST /entities/query` (`services/base/data-api`) is the likely successor for search |
| `dataset/series/{uid}`, `dataset/series/{uid}/thumbnail` | kept: no replacement on develop |
| `dataset/tag` | kept: no replacement on develop |
| `dataset/dashboard` | kept: no replacement on develop |
| `dataset/download` | kept: no replacement on develop |
| `get-static-website-result-reports` (admin router) | kept: no replacement on develop |
| `client/get-kaapana-instances`, `client/get-dags`, `client/get-ui-form-schemas`, `client/workflow` | kept; owned by base-ui's workflow dialog |

`dataset/fields` was called by an unused `loadDicomTagMapping` and is no longer
called.

## Dependencies

- `keycon` is no longer a direct dependency: its only use was an unused
  `KeyController`. `selecto` still brings its own copy (`npm ls keycon`).
- In-range updates are available (`npm outdated`: vue, vuetify, axios,
  apexcharts, vue-tsc, Playwright, sass-embedded, @vitejs/plugin-vue). Majors
  are behind as well: Vuetify 4, Vite 8, Pinia 4, Vue Router 5, TypeScript 7,
  ApexCharts 7, @koumoul/vjsf 4. Both are left to #2324.
- Version skew: this view resolves Vuetify 3.12.x, while `@kaapana/base-ui` is
  built against 3.13.x (both inside `^3.10`); the view's copy is the one used
  at runtime (Vite dedupe).

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
cluster needed. `fixtures/mock-backend.ts` intercepts every backend call with
`page.route`; it keeps its own copy of the datasets, addresses them by name and
access level like the backend, and honours `ids` clauses in queries.
`fixtures/helpers.ts` is the shared vocabulary of the specs: `openGallery()` to
boot, `failRoute()`/`delayRoute()`/`serverError()` to break or slow a call,
`nextRequest()`/`nextPost()`/`countRequests()` to observe calls, `toasts()` and
`expectNoToast()`, `confirmAction()`, `pressEscapeUntil()`/`dismissWithEscape()`,
`openFailureDetails()`, and `trackDirty()`/`lastDirty()` for the dirty state.

```bash
cd services/base/data-gallery-ui/docker/files
npx playwright test    # fixed port 4304 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing. There is no unit-test script.

Specs by concern:

| Spec | Covers |
| --- | --- |
| `boot` | fresh-profile boot, the gallery, card width, the "nothing yet" state, a failed first load |
| `search` | free text and link filters in the query, when the Search button spins, a failed copy of the link, why the Field and Values lists are empty |
| `datasets` | dataset scoping and the empty dataset, deep links, save / add / delete and their guards, access levels, the dataset lists' loading, empty and failed states |
| `confirmations` | the four confirmations: text, focus, size, colour, Escape, focus after confirming, progress and single submit |
| `feedback` | failed actions and their details dialog, download failures |
| `errors` | load failures, each reported once, inline or as one notification |
| `detail` | the detail pane: viewer, metadata, loading, failure, fast switching, a series without a study |
| `dashboard` | one request at boot, charts kept while reloading, bar-click filter, failed reload, label colour |
| `validation-report` | a report found, not found, failed lookup, failed fetch; the restart icon |
| `selection` | click, Ctrl-click and drag selection; tagging by card click |
| `tags` | tag chip state, removing a tag from a card |
| `view-dirty` | the dirty state posted to the shell, including after a remount |
| `lifecycle` | no timer outlives the viewer frame; lazy-card placeholders follow a resize |
| `gallery-modes` | structured mode, pagination |
| `project-scope` | every call carries the `/project/<slug>/` prefix; the unscoped redirect; moving to a linked project |
| `regressions` | pinned fixes from the Vuetify 2 → 3 migration and platform QA |
| `guidelines` | cross-cutting rules: accessible names, keyboard reach, unavailable actions, focus return, empty-state actions, validation, unsaved changes, shape, typeface |

## Open points

- **Keyboard selection of series cards.** Selection is Selecto mouse selection;
  keyboard users can act only on all shown series. Needs a design (a checkbox
  per card, or an `aria-multiselectable` grid).
- **Validation report HTML is injected with `v-html`** on the platform origin,
  which shares the session and `localStorage` with the other views. Whether the
  report generator can carry attacker-controlled markup from DICOM values needs
  a look.
- **The tag bar writes the shared `localStorage["settings"]`**, which fires a
  `storage` event in every other open same-origin view; their
  `useShellSettings` then remounts them.
- **Legacy routes.** Replacing the kaapana-backend routes above (see Legacy
  API) is for the leads to schedule.
- **Download confirmation.** Whether a download of at most 20 series needs a
  confirmation at all is a product decision; it now states the size limit.
- **Candidates for base-ui**: `useFocusReturn`, `notifyFailure` and the
  failure-details store (identical to extensions-ui's), `IFrameWindow`, and
  icon-map entries for download, copy and more.
- **Notification colours** come from `@kyvg/vue3-notification` defaults on
  every view, not from the theme.
