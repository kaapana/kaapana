# data-upload-ui

One of the Kaapana view apps (Vue 3 + Vuetify 3 + Vite SPA, served by nginx and
embedded as an iframe by the `portal-ui` shell). It lets a user get data into the
platform: instructions for the DICOM receiver port, browser-based (chunked) file
upload, and triggering an import workflow. Discovered by the shell via the
`kaapana.ai/ui.*` Ingress annotations (`data-upload-ui-chart/templates/service.yaml`)
and project-scoped through the `/project/<short_id>/` document URL prefix.

## Features

Single view (`src/views/DataUpload.vue`), two upload paths:

- **Option 1 — DICOM receiver port (preferred).** Static instructions with a
  ready-to-copy `dcmsend` example; the selected project's `short_id` is baked into
  the `--call kp-<short_id>` AE title and `window.location.hostname` into the host.
- **Option 2 — browser upload (experimental).** A FilePond dropzone
  (`src/components/Upload.vue`) doing **chunked uploads** (1 MiB chunks, `chunkForce`):
  a POST returns a transfer id, then one PATCH per chunk, DELETE reverts an uploaded
  file ("Remove from list"), HEAD is the resume probe. `beforeAddFile` stamps a
  `filepath` metadata field (relative path or filename). Accepts any file type;
  `multiple` uploads allowed.
- **Info dialog** explaining the expected zip layout for DICOM and NIfTI data.
- **Import workflow dialog** — the shared `WorkflowExecution` component from
  `@kaapana/base-ui/workflow-execution`, opened by "Import the data", pinned to
  `onlyLocal` + `kind_of_dags="import"`. Fields are restyled to the `underlined`
  variant via a local `v-defaults-provider`. On success the dropzone is remounted
  (`componentKey` bump) so a new batch can be uploaded.
- **Archived project → read-only.** When `selectedProject.is_archived`, a warning
  alert shows and the browser-upload card is disabled (the DICOM-port card stays).

## Backend endpoints

Runtime calls the app makes. The **Scope** column marks whether the request passes
through the `@kaapana/base-ui` `httpClient` interceptor, which rewrites URLs
matching `^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/` to
`/project/<short_id>/…` (the `short_id` from the document URL). Everything else is
sent as-is.

| Method | Path | Purpose | Scope |
| --- | --- | --- | --- |
| GET | `/oauth2/userinfo` | Auth gate (`useAuthStore.checkAuth`, run in `router.beforeEach`); dev fallback `/jsons/testingAuthenticationToken.json` when not `PROD` | unscoped |
| GET | `/aii/users/current` | Current user id + realm roles (project store `getSelectedProject`) | unscoped |
| GET | `/aii/projects` (admin) or `/aii/users/<id>/projects` (non-admin) | Project list; the URL slug is resolved against it, else the document is redirected onto the first project | unscoped |
| POST | `/kaapana-backend/client/file` | FilePond: request a transfer id (carries `Upload-Length` + `filepath`) | scoped (manual prefix — see note) |
| PATCH | `/kaapana-backend/client/file?patch=<id>` | FilePond: upload one chunk (tus-style `Upload-Offset`/`Upload-Name`) | scoped (manual prefix) |
| DELETE | `/kaapana-backend/client/file` | FilePond: revert an uploaded file (transfer id in body) | scoped (manual prefix) |
| HEAD | `/kaapana-backend/client/file` | FilePond: resume probe | scoped (manual prefix) |
| POST | `/kaapana-backend/client/get-kaapana-instances` | Import dialog: list runner instances (`onlyLocal` keeps the local one) | scoped |
| POST | `/kaapana-backend/client/get-dags` | Import dialog: importable dags (`kind_of_dags="import"`) | scoped |
| POST | `/kaapana-backend/client/get-ui-form-schemas` | Import dialog: per-dag vjsf form schemas | scoped |
| POST | `/kaapana-backend/client/workflow` | Import dialog: submit the workflow | scoped |
| GET | `/kaapana-backend<backend-route>` | Import dialog, **conditional**: only when a dag's schema declares `backend_form["backend-route"]` — fetches file-tree items (optional `?prefix=` for children) | scoped |

The `oauth2`/`aii` and `client/*` calls go through `@kaapana/base-ui` (`AuthService`,
the project store, and `WorkflowExecution` via `kaapanaApiService`). This app **owns
the project store** — `DataUpload.vue` dispatches `getSelectedProject()` itself (the
shell no longer does).

> **Note — FilePond bypasses `httpClient`.** FilePond issues its own XHR, so the
> axios interceptor never sees the upload requests; `Upload.vue` applies the
> `/project/<short_id>` document prefix itself via `getProjectBase()` (same
> pattern as extensions-ui). Asserted in `tests/e2e/upload.spec.ts` (exact
> `pathname` `/project/admin/kaapana-backend/client/file`).

(`.env` defines `VITE_KAAPANA_BACKEND_ENDPOINT` / `VITE_NOTIFICATIONS_API_ENDPOINT`,
but nothing in `src/` reads `import.meta.env` — they are inert; the upload URL is
hardcoded in `Upload.vue`.)

## Development

`@kaapana/base-ui` is a `file:` dependency consumed as its built `dist/`, so build
the library first (and re-run the build after any change to its `src/`):

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build
```

Then run this view from its `docker/files`:

```bash
cd services/base/data-upload-ui/docker/files
npm ci
npm run dev            # Vite dev server on http://localhost:5000
```

The app is served under `base: /data-upload-ui/`. In the platform it is reached
through the shell at `/project/<short_id>/data-upload-ui/`. The dev/preview server
strips the `/project/<short_id>/` prefix like traefik does (see `vite.config.ts`),
so the project-scoped URL works locally too; served without the prefix, the view
redirects onto the user's first project.

## Tests

Mock-backed Playwright e2e under `docker/files/tests/e2e` — no backend or cluster
needed; `fixtures/mock-backend.ts` intercepts every backend call with `page.route`
and seeds `localStorage["settings"]`; the project is **not** seeded — it travels in
the document URL.

```bash
cd services/base/data-upload-ui/docker/files
npx playwright test    # fixed port 4302 (portal-ui 4300, views 4301-4309)
```

Locally the suite runs against the dev server; in CI (`ui_e2e_tests`) it previews
the production build. Rebuild `@kaapana/base-ui` (`npm run build`) after any change
to its `src/` before running tests — consumers otherwise import the stale `dist/`
through the npm symlink and nothing errors, the change is just missing.

Suites: `render`, `upload` (chunked protocol, error state, revert), `import`
(workflow load/submit, error, cancel, data_form dataset lift), `project-scope`
(URL-derived scoping + redirect).
