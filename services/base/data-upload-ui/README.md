# data-upload-ui

One of the Kaapana view apps (Vue 3 + Vuetify 3 + Vite SPA, served by nginx and
embedded as an iframe by the `portal-ui` shell). It lets a user get data into the
platform: instructions for the DICOM receiver port, browser-based (chunked) file
upload, and triggering an import workflow. Discovered by the shell via the
`kaapana.ai/ui.*` Ingress annotations (`data-upload-ui-chart/templates/service.yaml`)
and project-scoped through the `/project/<short_id>/` document URL prefix.

## Features

Single view (`src/views/DataUpload.vue`), two upload paths:

- **Option 1 — DICOM receiver port (preferred).** Instructions with a `dcmsend`
  example in a code block with a "Copy command" button. The selected project's
  `short_id` is baked into the `--call kp-<short_id>` AE title and
  `window.location.hostname` into the host; until the project is known, the example
  shows `kp-<project-short-id>`. Hints state that `11112` is the default receiver
  port and that the dataset name can have at most 13 characters after `kp-`.
- **Option 2 — browser upload (experimental).** Three numbered steps. A FilePond
  drop zone (`src/components/Upload.vue`) does **chunked uploads** (1 MiB chunks,
  `chunkForce`): a POST returns a transfer id, then one PATCH per chunk; DELETE is
  sent by "Remove from list"; HEAD is the resume probe. `beforeAddFile` stamps a
  `filepath` metadata field (relative path, else the file name). Accepts any file
  type; multiple files are allowed. The drop zone's colours and font are
  mapped onto the Vuetify theme roles.
- **Unsaved uploads.** `Upload.vue` emits `uploading` while any file is queued or
  uploading; the view forwards it to `postViewDirty`, so the shell warns before a
  project switch or refresh reloads the view.
- **Info dialog** (600 px) explaining the expected zip layout for DICOM and NIfTI
  data, with a link to the NIfTI section of the user guide.
- **Import workflow dialog** (600 px) — the shared `WorkflowExecution` component
  from `@kaapana/base-ui/workflow-execution`, opened by "Import the data", pinned to
  `onlyLocal` + `kind_of_dags="import"`. The button stays enabled while uploads
  run. The dialog content unmounts when the dialog closes, so each opening loads
  the current list of uploaded files. Fields use the `outlined` variant, set in
  `src/plugins/vuetify.ts`.
- **Archived project → read-only.** When `selectedProject.is_archived`, a warning
  alert shows, and the drop zone and the import button are disabled (the
  DICOM-port card stays).
- **Project lookup failure.** An inline error alert with "Try again" and "Details"
  (the shared `ErrorDetailsDialog`).

Vuetify is created with `createKaapanaVuetify()`, and `main.ts` imports
`@kaapana/base-ui/style.css`. Icons for actions come from `kaapanaIcons`.

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
| POST | `/kaapana-backend/client/file` | FilePond: request a transfer id (carries `Upload-Length` + `filepath`) | prefixed by `Upload.vue` (see note) |
| PATCH | `/kaapana-backend/client/file?patch=<id>` | FilePond: upload one chunk (tus-style `Upload-Offset`/`Upload-Name`) | prefixed by `Upload.vue` |
| DELETE | `/kaapana-backend/client/file` | FilePond "Remove from list" (transfer id in body); the backend deletes only the partial upload data of that transfer | prefixed by `Upload.vue` |
| HEAD | `/kaapana-backend/client/file` | FilePond: resume probe | prefixed by `Upload.vue` |
| POST | `/kaapana-backend/client/get-kaapana-instances` | Import dialog: list runner instances (`onlyLocal` keeps the local one) | scoped |
| POST | `/kaapana-backend/client/get-dags` | Import dialog: importable dags (`kind_of_dags="import"`) | scoped |
| POST | `/kaapana-backend/client/get-ui-form-schemas` | Import dialog: per-dag vjsf form schemas | scoped |
| POST | `/kaapana-backend/client/workflow` | Import dialog: submit the workflow | scoped |

The `oauth2`/`aii` and `client/*` calls go through `@kaapana/base-ui` (`AuthService`,
the project store, and `WorkflowExecution` via `kaapanaApiService`). This app **owns
the project store** — `DataUpload.vue` dispatches `getSelectedProject()` itself (the
shell no longer does).

> **Note — FilePond bypasses `httpClient`.** FilePond issues its own XHR, so the
> axios interceptor never sees the upload requests; `Upload.vue` applies the
> `/project/<short_id>` document prefix itself via `getProjectBase()` to its
> `UPLOAD_URL` (same pattern as extensions-ui). Asserted in `tests/e2e/upload.spec.ts` (exact
> `pathname` `/project/admin/kaapana-backend/client/file`).

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

Suites: `render` (both upload options, info dialog, `dcmsend` hints and copy,
archived project, project lookup failure and retry), `upload` (chunked protocol
incl. multi-chunk files, `filepath` metadata, error state, revert), `import`
(workflow load/submit, error, cancel, data_form dataset lift), `upload-import`
(an open import form keeps its input when an upload finishes; reopening reloads
the file list), `view-dirty` (`kaapana:view-dirty` for running, finished, failed,
aborted and parallel uploads), `guidelines` (typeface, type scale, icons, width,
dialog sizes and focus, field variant, theme roles and drop zone colours in both
themes), `project-scope` (URL-derived scoping + redirect).
