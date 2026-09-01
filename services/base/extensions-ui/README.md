# extensions-ui

The **Extensions** view — one of the Kaapana view apps (Vue 3 + Vuetify 3 +
Vite SPA, served by nginx and embedded as a same-origin iframe by the
`portal-ui` shell). It manages Helm-chart based platform extensions
(applications and workflows) — installing, uninstalling, updating, versioning,
and parameterizing them against the `kube-helm-api` backend. Discovered via the
`kaapana.ai/ui.*` Ingress annotations and scoped to a project through the
`/project/<short_id>/` document-URL prefix.

> Not to be confused with the adjacent `services/base/extension-manager-ui`,
> a separate newer service (backed by `extension-manager-service`, OCI-registry
> catalog + repository management). `extensions-ui` is the legacy-derived
> `kube-helm-api` view and is the one described here.

The whole app lives under `docker/files/`; the single view is
`src/views/Extensions.vue`.

## Features

Derived from `src/views/Extensions.vue` and the e2e specs:

- **Extension table** — one row per extension, columns: Type
  (application `mdi-application-outline` / workflow-DAG `mdi-gamepad-variant`),
  Name + truncated description + docs link (`/docs/…` from the chart's
  `documentation` annotation), Version, Maturity
  (Experimental / Stable), Hardware requirement (CPU / GPU), Action, Ready, and
  external Links (opened in new tabs). Display name comes from `display_name`,
  falling back to the `ui-visible-name` annotation, then the release name.
- **Filtering** — free-text Search plus three per-column filter menus: Type
  (Applications / Workflows), Maturity (Experimental / Stable), Hardware
  (CPU / GPU). Experimental extensions are hidden by default (only Stable is
  pre-selected).
- **Install / Launch lifecycle** — non-multi-installable extensions show
  *Install*, multi-installable ones *Launch*. When the extension declares
  `extension_params`, a configuration dialog opens first; otherwise the install
  fires immediately. The form renders parameter types `string`, `bool`/
  `boolean`, `list_single`, `list_multi`, plus `group_name` and `doc`
  (rich-text/HTML) section markers, with per-field validation and help
  tooltips. A just-launched multi-instance briefly shows a disabled *Launched*
  state.
- **Uninstall / Delete** — installed extensions show *Uninstall* (single) or
  *Delete* (multi-installable). A stuck *Pending* install exposes a
  *Force Uninstall / Force Delete* action that passes `--no-hooks`.
- **Version selection** — a per-row dropdown (`versions`) chooses which chart
  version the action targets; the selected version flows into the
  install/uninstall payload.
- **Ready / resource state** — the Ready column reflects the deployment state
  derived from `available_versions[version].deployments[0]`: an indeterminate
  spinner while `pending`, a red `mdi-alert-circle` on failure, a green
  `mdi-check-circle` when ready; the tooltip surfaces the aggregated Helm
  status and Kubernetes pod status.
- **Polling & refresh** — the list is re-fetched every 5 s. The cloud-refresh
  control triggers a backend re-download of the latest extensions
  (`update-extensions`).
- **Upload** — a FilePond drop zone (chunked upload) accepts extension charts
  (`.tgz`) and container images (`.tar`); an uploaded `.tar` is then imported
  via `import-container`.

## Backend endpoints

Every runtime call the app makes. The **Scope** column marks how each is
prefixed with the `/project/<short_id>` document prefix.

### `kube-helm-api` (extension marketplace) — via `kaapanaApiService`

| Method | Endpoint | Purpose | Scope |
| --- | --- | --- | --- |
| GET  | `/kube-helm-api/extensions?repo=kaapana-public` | List all extensions (polled every 5 s). | interceptor |
| GET  | `/kube-helm-api/update-extensions` | Re-download the latest extensions (refresh control). GET despite mutating. | interceptor |
| GET  | `/kube-helm-api/import-container?filename=<f>` | Import an uploaded container `.tar`. GET despite mutating. | interceptor |
| POST | `/kube-helm-api/helm-install-chart` | Install / launch a chart (`{name, version, keywords, extension_params?}`). | interceptor |
| POST | `/kube-helm-api/helm-delete-chart` | Uninstall / delete (`{release_name, release_version, helm_command_addons}`; `--no-hooks` for force). | interceptor |
| POST | `/kube-helm-api/filepond-upload` | Chunked chart/container upload (FilePond). | manual |

### `@kaapana/base-ui` internals (triggered by this app)

| Method | Endpoint | Purpose | Scope |
| --- | --- | --- | --- |
| GET | `/oauth2/userinfo` (prod) · `/jsons/testingAuthenticationToken.json` (dev) | Auth check per navigation (`useAuthStore().checkAuth`); failure is swallowed, the gateway enforces auth in front of the iframe. | none |
| GET | `/aii/users/current` | Current user, to pick the project-list URL. | none |
| GET | `/aii/projects` (admin) · `/aii/users/<id>/projects` (non-admin) | Resolve the URL slug against the user's projects; an unscoped document redirects onto the first project. **This app HAS the project store.** | none |
| GET | `/jsons/commonData.json` | `commonDataStore.loadCommonData()`. Ported from the monolith; the fetched value is **never read** by the view (vestigial). | none |

**Scope tiers**

- **interceptor** — the `httpClient` request interceptor (`PROJECT_SCOPED` =
  `^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/`) rewrites
  the URL to `/project/<short_id>/kube-helm-api/...`; the gateway authorizes
  the slug and injects the trusted `Project` header before stripping the
  prefix.
- **manual** — FilePond bypasses `httpClient`, so `Upload.vue` prepends
  `getProjectBase()` itself; project-scoped but *not* via the interceptor.
- **none** — auth, `/aii/*`, and the `/jsons/*` static files are not
  project-scoped.

> The `commonData` store also defines `getPolicyData`
> (`GET /kaapana-backend/open-policy-data`), but this view **does not call it**
> — no policy request is made at runtime. The vuex module it was ported from
> also had `checkAvailableWebsites` / `getExternalWebpages`; neither survived
> the port, so no external-webpages, traefik-routes or os-dashboards call
> exists here either.

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
cd services/base/extensions-ui/docker/files
npm ci
npm run dev            # Vite dev server on http://localhost:5000
```

The app is served under the `/extensions-ui/` base, so open
`http://localhost:5000/extensions-ui/`. In the platform it is reached through
the shell at `/project/<short_id>/extensions-ui/`; the dev/preview server
strips the `/project/<short_id>/` prefix like traefik does (see
`vite.config.ts`), so the project-scoped URL works locally too.

Production serves the static `dist/` from the nginx image on port `5000`
(`nginx.conf`); the container is built via a `local-only/base-ui:latest` base
stage (see `docker/Dockerfile`).

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or
cluster needed; `fixtures/mock-backend.ts` intercepts every backend call with
`page.route` (fixture shapes mirror the `kube-helm` `KaapanaExtension` schema).

```bash
cd services/base/extensions-ui/docker/files
npx playwright test    # fixed port 4303 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it
previews the production build. Rebuild `@kaapana/base-ui` (`npm run build`)
after any change to its `src/` before running tests — consumers otherwise
import the stale `dist/` through the npm symlink and nothing errors, the
change is just missing.

Suites: `list`, `filter`, `install`, `uninstall`, `polling`, `project-scope`.
