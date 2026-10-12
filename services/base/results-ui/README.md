# results-ui

The **Workflow Results** browser — one of the Kaapana view apps (Vue 3 +
Vuetify 3 + Vite SPA, served by nginx and embedded as an iframe by the
`portal-ui` shell). Discovered through the `kaapana.ai/ui.*` Ingress
annotations on its chart and project-scoped purely by the
`/project/<short_id>/` prefix on the document URL. The view is a lazy-loaded tree of the result files produced by
workflow runs, with an accordion of in-iframe file previews on the right.

## Features

Single view, `src/views/ResultsBrowser.vue`:

- **Lazy tree browser** — a left-hand `v-treeview` of result folders and files.
  Only the first page loads on mount; expanding a folder fetches its children on
  demand (`:load-children`), and each folder pages independently.
- **Paging ("Load more")** — every listing is fetched in bounded pages of
  `limit=100` (VTreeview has no virtualization, so a large page would freeze the
  tab). A "Load more root results" button pages the top level; a per-folder
  "Load more" appended to a folder row pages that folder. On a paging error the
  continuation token is kept so the button stays retryable.
- **Selecting a file → preview** — checking a file adds an accordion panel on the
  right that loads the file's `url` in an iframe (`IFrameWindow.vue`); checking
  several opens one panel each, and the newest expands. Panels are keyed by
  result path, so unchecking one leaves the others as they are. Each panel header
  has a button that opens the file in a new tab, labelled with the result's name
  and carrying the url in its tooltip. Unchecking a file removes its panel.
- **Folder cascade (check a folder → open all its files)** — checking a folder
  walks its whole subtree (fetching unloaded descendants and draining
  continuation pages) and opens a panel per result file. Guards: a confirm
  dialog above 10 files, a hard cap of 300 files per cascade (with a truncation
  warning), stop-not-storm on a mid-cascade fetch error, one confirm at a time,
  and re-checks that the folder is still selected after the async fetch.
  Unchecking a folder prunes its descendants from the selection by path prefix.
  The confirm dialog opens with **Cancel** focused; Cancel, Escape and a click
  outside all cancel and uncheck the folder again.
- **Search** — a text field filters the tree. Note (the field's own hint says
  so): it only filters folders and files **already loaded** — it is not a
  backend search. A search that matches nothing offers to clear itself.
- **File-type icons** — tree rows show an extension-based icon for
  `html/js/json/md/pdf/png/txt/xls`, and a generic file icon for anything else.
  Display only; every file previews identically in an iframe regardless of type.
- **Empty / error states** — an empty listing says that no results exist yet; a
  failed root fetch shows an inline alert with a **Retry** button in place of the
  tree; a failed folder fetch or paging call reports through a notification and
  leaves the loaded rows in place.
- **Layout** — the tree and the preview sit side by side above the `md`
  breakpoint and stack below it. The view is capped at 2100 px wide.

## Theme and typeface

`src/plugins/vuetify.ts` returns `createKaapanaVuetify()` from
`@kaapana/base-ui`, which carries the Kaapana light and dark themes, the mdi
icon aliases and the platform typeface (Roboto). `App.vue` follows the shell's
dark-mode setting through `useShellSettings()`. Icons for actions that exist
across views come from the shared `kaapanaIcons` map rather than from `mdi-*`
names at the call site.

## Backend endpoints

Every runtime network call. Only `/kaapana-backend/...` is project-prefixed —
the httpClient interceptor in `@kaapana/base-ui` rewrites paths matching
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` to
`/project/<short_id>/…` using the slug from the document URL. Auth and the file
url are **not** prefixed. This app has **no** project store and makes **no**
`/aii` calls.

| Method & path | Project-scoped | Purpose |
| --- | --- | --- |
| `GET /kaapana-backend/get-static-website-results-tree?limit=100` | yes | Root listing (first page). |
| `GET …get-static-website-results-tree?prefix=<path>&limit=100` | yes | Lazy-load one folder's children. |
| `GET …get-static-website-results-tree?continuation_token=<t>&limit=100` | yes | Next page of the root listing. |
| `GET …get-static-website-results-tree?prefix=<path>&continuation_token=<t>&limit=100` | yes | Next page of a folder's children. |
| `GET /oauth2/userinfo` (prod) / `GET /jsons/testingAuthenticationToken.json` (dev) | no | Userinfo JWT; run on every navigation via a router `beforeEach` (`useAuthStore().checkAuth()`). Non-blocking — a failure is logged and navigation proceeds. |
| `GET <file node url>` (iframe `src` + `window.open`) | no | Load/open a result file. The url is whatever the backend puts on the node — the app does not construct it. (In the e2e mock it is `/minio-console/download/results/<path>`.) |

The four rows above are all the same endpoint in different query-param modes.
`src/api/results.ts` wraps it as `fetchResultsTree()` over the shared
`httpClient`; the auth call goes through `httpClient` as well.

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
cd services/base/results-ui/docker/files
npm ci
npm run dev        # Vite dev server on http://localhost:5000
```

Standalone the app lives at `http://localhost:5000/results-ui/`. In the
platform it is reached through the shell at `/project/<short_id>/results-ui/`.
The dev/preview server strips the `/project/<short_id>/` prefix like traefik
does (see `vite.config.ts`), so the project-scoped URL works locally too and
the backend calls carry the same project prefix.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route`.

```bash
cd services/base/results-ui/docker/files
npx playwright test    # fixed port 4306 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing.

Suites cover render, navigation (lazy load + independent folders + search),
pagination, folder cascade, cascade errors, preview, project-scope, error
handling, and presentation (typeface and dark theme).
