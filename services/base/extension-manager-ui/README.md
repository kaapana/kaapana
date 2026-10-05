# extension-manager-ui

The **Extension Manager** view — one of the Kaapana view apps (Vue 3, Vuetify 3,
Vite SPA, served by nginx and embedded as a same-origin iframe by the
`portal-ui` shell). It is the frontend of `extension-manager-service`, which
distributes extensions packaged as OCI artifacts. It is discovered via the
`kaapana.ai/ui.*` Ingress annotations and listed in the **Experimental**
section of the navigation. It is project-agnostic: the iframe is not prefixed
with `/project/<short_id>/`.

> Not to be confused with the adjacent `services/base/extensions-ui`, the
> supported Helm-chart based **Extensions** view backed by `kube-helm-api`.

The whole app lives under `docker/files/`:

| Path | Purpose |
| --- | --- |
| `src/App.vue` | Page title, the section tabs, notifications, the one failure-details dialog, shell settings. |
| `src/router/router.ts` | The three sections `/catalog`, `/extensions`, `/repositories`; `/` and unknown paths go to the catalog. |
| `src/views/` | One view per section: `Catalog.vue`, `Extensions.vue`, `Repositories.vue`. |
| `src/features/catalog/` | Filter bar, the catalog entry dialog, grouping/filtering and the install-availability rules. |
| `src/features/extensions/` | The installed-extension dialog (status, contents, uninstall) and its API calls. |
| `src/features/repositories/` | The repository form dialog (create/edit, validation, unsaved-changes protection), form adapter and API calls. |
| `src/shared/components/` | Card grid, detail dialog, status indicator, manifest and source details used by more than one section. |
| `src/shared/utils/status.ts` | User-facing labels and tones for every extension and content status of the service. |
| `src/shared/utils/notify.ts` | Transient success and failure notifications; a failure carries its details. |
| `src/shared/composables/usePolling.ts` | Interval polling that runs only while an operation is in progress. |

## `@kaapana/base-ui`

The app consumes `@kaapana/base-ui` for the theme, typeface and icon map
(`createKaapanaVuetify`, `kaapanaIcons`), shell integration
(`useShellSettings`, `postViewDirty`), the shared dialogs (`ConfirmDialog`,
`ErrorDetailsDialog`), error helpers (`apiErrorInfo`, `apiErrorText`) and
`httpClient`. It no longer ships its own theme, dark-mode toggle, app bar,
confirmation dialog or error helpers.

Everything in `src/shared/` stays local to this view; nothing is moved to
`base-ui`. `notifyFailure` and the failure-details store are a copy of the
`extensions-ui` ones, kept on purpose for now.

## Features

- **Catalog** — one card per extension and repository, with the number of
  versions, the latest version and the installation state of the newest
  installed version. Search (name, version, repository name or URL) and a
  repository filter. A card opens a dialog with a version selector, the
  repository and tag, the manifest contents and dependencies, and the raw
  manifest.
- **Install** — installs the selected version. The button says why it is
  unavailable when the version is installed, being installed or uninstalled,
  or when a failed uninstall blocks it; after a failed installation it offers
  *Retry installation*. Progress is shown on the button, it cannot be
  submitted twice, and the outcome is a transient notification.
- **Extensions** — every extension with platform state: repository, tag,
  version and status in user terms (*Downloading*, *Installation failed*, …),
  carried by an icon and a label. The list is polled every 5 s while an
  operation is in progress and not at all otherwise.
- **Uninstall** — from the extension's dialog, after a confirmation that names
  the version, the repository and the installed items. Unavailable, with an
  explanation, while an operation runs; hidden for uninstalled extensions.
- **Repositories** — add, edit and remove OCI repositories. Fields are
  validated with messages that say how to fix the value. When editing, the
  stored credentials are kept unless both username and password are entered.
  Closing an edited form asks before discarding, and an edited form reports
  the view as dirty to the shell. Removing a repository is confirmed and says
  that extensions installed from it stay installed and can still be
  uninstalled; they show "Repository removed" afterwards.
- **Empty and failure states** — each section distinguishes "nothing yet"
  (with the next step), "nothing matches" (catalog: clear filters) and "could
  not load" (retry and details). A failed refresh keeps the last list with an
  inline warning; a repository whose manifests cannot be loaded is named in a
  warning while the others stay visible.
- **Feedback** — action outcomes are transient notifications. Selecting a
  failure notification, or *Details* on an alert, opens the failure-details
  dialog with status code, request line, backend message and a copy button.

## Backend endpoints

All calls go to `extension-manager-service` through the
`/extensions-api` Ingress (traefik strips the prefix). None is project-scoped.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/extensions-api/repositories` | List repositories (all three sections). |
| POST | `/extensions-api/repositories` | Register a repository (`name`, `description`, `repository_url`, `username`, `password`). |
| PUT | `/extensions-api/repositories/<id>` | Update a repository; `username`/`password` only when both are replaced. |
| DELETE | `/extensions-api/repositories/<id>` | Remove a repository; its installed extensions keep their records with `repository_id: null`. |
| GET | `/extensions-api/repositories/<id>/extensionManifests` | Tags and manifests of the extensions published in a repository (30 s timeout, one call per repository). |
| GET | `/extensions-api/extensions` | Extensions with platform state (polled while one is in progress). |
| POST | `/extensions-api/extensions/install?repository_id=<id>&tag=<tag>` | Start an installation. |
| POST | `/extensions-api/extensions/<id>/uninstall` | Start an uninstall. |

**Legacy APIs:** none. The app calls no `kaapana-backend`, `kube-helm-api`,
`/aii` or `/oauth2` endpoint; authentication is enforced by the gateway in
front of the iframe. It reads only the shell's `localStorage["settings"]`.

### Known backend limitations (proposal)

In `extension-manager-service`; the UI works around it today.

#### A just-uninstalled version cannot be reinstalled for 30 s

When an uninstall finishes, the record moves to `uninstalled`, which has no
allowed transition, and the background task deletes it after `sleep(30)`. A
reinstall of the same repository and tag in that window answers `409`
(`uq_repository_id_tag`). The UI keeps polling while a record is
`uninstalled`, disables *Install* with "It can be installed again in a
moment", and enables it once the record is gone.

Allowing `UNINSTALLED → PENDING` (and `UNINSTALLED → INSTALLING` for the
contents) does **not** interrupt an uninstall: the record only reaches
`uninstalled` after every content was uninstalled. The hazard is the delayed
cleanup. `delete_extension` reads the status, then deletes in a separate
statement without a row lock. A reinstall that moves the record to `pending`
between the two lets the cleanup delete a record whose installation is
running; its contents could then be installed in the target service with no
record left to uninstall them.

| Option | Change | Effect |
| --- | --- | --- |
| **A. Leave it** | None. | 30 s wait, handled by the UI. |
| **B. Reinstall + drop the cleanup** | Allow the two transitions; remove `sleep(30)` and `delete_extension`. | Immediate reinstall; `uninstalled` records stay and are reused. The *Extensions* page then shows them (or filters them). |
| **C. Reinstall + atomic cleanup** | Allow the two transitions; make the cleanup a single `DELETE … WHERE id = :id AND status = 'uninstalled'`. | Immediate reinstall inside the window; the record still disappears after 30 s when nobody reinstalled it. |

Recommendation: **A** for now; **C** if the wait matters. Do not allow the
transitions without changing the cleanup.

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
cd services/base/extension-manager-ui/docker/files
npm ci
npm run dev            # Vite dev server on http://localhost:5173/extension-manager-ui/
```

The dev server proxies `/extensions-api` to the in-cluster service, so outside
a cluster use the e2e mocks below. Production serves the static `dist/` from
the nginx image on port `5000` (`nginx.conf`); the image is built on the
`local-only/base-ui:latest` base stage (see `docker/Dockerfile`).

**In-cluster dev loop:** run `npm ci` in `docker/files` on the host, switch the
`Dockerfile` to its development part, set `global.dev_files` in
`extension-manager-ui-chart/values.yaml` to the host path of `docker/files`, and
deploy. The chart then mounts the sources into the container and serves Vite
with hot module reload on port `5173`.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed. `fixtures/mock-backend.ts` serves every `/extensions-api` call
from an in-memory state that the actions change (an install adds a record, an
uninstall moves it to *Uninstalling*), with shapes taken from the service's
pydantic schemas. `fixtures/helpers.ts` holds the shared vocabulary:
`openView()`, `card()`, `dialog()`, `nextRequest()`, `countRequests()`,
`failRoute()`, `confirmAction()`, `pressEscapeUntil()`,
`openFailureDetails()` and `recordShellMessages()`.

```bash
cd services/base/extension-manager-ui/docker/files
npx playwright test    # fixed port 4311
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build.

| Spec | Covers |
| --- | --- |
| `boot` | fresh-profile boot, the shell's dark-mode setting, no own app bar/theme toggle, routing and the section tabs |
| `catalog` | grouping, detail dialog, keyboard access, search and repository filter, the empty states, load failure, one failing repository |
| `install` | install payload for the selected version, unavailable/retry states, no double submit, polling to the settled state, a rejected install |
| `extensions` | status labels, per-item status, uninstall confirmation and payload, dismissal, unavailable/hidden uninstall, polling start and stop, failures, empty and stale states |
| `repositories` | create payload, validation messages, rejected create, edit payload and credential rules, unsaved-changes protection, `kaapana:view-dirty`, removal and its consequences |
| `guidelines` | cross-cutting rules: confirmations, focus return, theme and typeface, readable width, one primary action per page, status not by colour alone, accessible names, dialog widths |

## Leaving the Experimental section (proposal)

To be agreed with the Kaapana Leads. The view can replace `extensions-ui` and
leave the Experimental section once:

1. `extension-manager-service` has installers for every content type the
   platform distributes today through Helm charts (applications as well as
   workflows), so `extensions-ui` has no remaining use case.
2. The extensions currently published as Helm charts are available as OCI
   extensions in a default repository that a fresh platform registers.
3. The backend limitations above are resolved (reinstall after uninstall,
   repository removal with installed extensions).
4. Access is decided for non-admin users. Today OPA grants
   `/extension-manager-ui` and `/extensions-api` to the admin role only; if
   other roles get read access, the view must hide the write controls
   (repositories, install, uninstall) for them, as `extensions-ui` does.

`extensions-ui` then stays for one release as a fallback and is removed
afterwards.
