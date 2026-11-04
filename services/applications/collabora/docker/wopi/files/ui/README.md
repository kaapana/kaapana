# Collabora documents UI

The document browser of the Collabora application, shown as **Documents** in
the Store section of the navigation. It lists the office documents stored in
MinIO and opens each one in Collabora Online in a new tab.

It is a Vue 3 + Vuetify 3 + Vite SPA, built into the `kaapana-wopi` image and
served by the WOPI backend (`../../app`, FastAPI) from `/app/ui/dist` under
`/collabora-wopi/`. The menu entry comes from the `kaapana.ai/ui.*`
annotations on the `collabora-chart-wopi` Ingress
(`collabora-chart/templates/service.yaml`).

## Deviations from the default UI stack

- **Served by FastAPI, not nginx.** The UI and the WOPI API share one
  container and one origin, which the relative API and WebSocket URLs rely on.

## Project scope

The Ingress declares `kaapana.ai/ui.project: "path"`, so the shell loads the
view under `/project/<short_id>/collabora-wopi/`. The relative API and
WebSocket URLs inherit that prefix, the `collabora-chart-wopi-project-ingressroute`
strips it, and auth-backend adds the `Project` header. The backend lists only
the documents in that project's bucket and only announces updates to views of
the same project.

## Features

- Browses the documents as folders, built from the `/` in their object paths:
  folders first, each with its document count and latest change, then the
  files with modification date and size. Breadcrumbs lead back up; after a
  reload the view stays in the deepest folder that still exists.
- Sorts by name (natural order) or last modified.
- Search covers all folders and lists the matching documents with their full
  path, case-insensitively.
- The backend lists MinIO on every request, so **Refresh** just reloads the
  list.
- Reloads the list when the backend announces an update over the `ws`
  WebSocket (after Collabora saved a document of the project), and reconnects
  5 s after the socket drops.
- Distinct states for loading, no documents, no search match and a failed
  request; a failure offers the request details and a retry.
- Follows the shell's dark-mode setting.

## Backend endpoints

All paths are relative to the document, so they resolve under
`/project/<short_id>/collabora-wopi/`. See `../README.md` for the WOPI side.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `documents/` | List the project's documents with the Collabora URL that opens each one; `503` until Collabora was discovered |
| WebSocket | `ws` | `{"type": "update"}` after a document of the project was saved |

## What comes from `@kaapana/base-ui`

`createKaapanaVuetify` (theme, icons, bundled Roboto), `useShellSettings`
(dark mode), `kaapanaIcons`, `ErrorDetailsDialog`, `apiErrorText` and
`apiErrorInfo`. The library is a `file:` dependency on
`services/base/base-ui/docker/files`; the Dockerfile copies it from the
`local-only/base-ui` image to the same relative path.

## Development

Build the library first, and again after every change to its `src/`:

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build
```

Then build the view:

```bash
cd services/applications/collabora/docker/wopi/files/ui
npm ci
npm run build      # type-check, then build dist/
```

There is no dev server: the view only works behind the platform, which adds
the project prefix, the `Project` header and the token. Check changes with the
Playwright suite and in a deployment.

Linting and formatting use the repository-wide ESLint/Prettier setup; see
`docs/source/development_guide/code_formatting.rst`.

## Tests

A mock-backed Playwright suite in `tests/e2e`. `fixtures/mock-backend.ts`
answers the two HTTP endpoints with `page.route` and the WebSocket with
`page.routeWebSocket`, using the types from `src/api/documents.ts`.

```bash
npx playwright test
```

The suite runs on port 4313 against a `vite preview` of the production build,
locally and in CI, where the `ui_e2e_tests` job
runs it.

| Spec | Covers |
| --- | --- |
| `boot.spec.ts` | Fresh-profile boot, dark mode from the shell |
| `list.spec.ts` | One request on open, folders and breadcrumbs, sorting, search, links, empty and loading states |
| `feedback.spec.ts` | Failures, retry, refresh progress, live updates, reconnect |
| `guidelines.spec.ts` | Typeface, content width, action hierarchy, icon map |
