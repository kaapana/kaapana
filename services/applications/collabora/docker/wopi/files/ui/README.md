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
- **Not project-scoped.** The Ingress declares no `kaapana.ai/ui.project`, so
  the shell loads the view without a `/project/<short_id>/` prefix. The backend
  lists the documents of every MinIO bucket regardless of the selected project.

## Features

- Lists the documents with their bucket and modification time, newest first,
  or sorted by path.
- Filters by path, case-insensitively.
- **Check for new documents** makes the backend rescan MinIO. The view does
  this once when it opens, because the backend only finds documents on a
  rescan.
- Reloads the list when the backend announces an update over the `ws`
  WebSocket, and reconnects 5 s after the socket drops.
- Distinct states for loading, no documents, no search match and a failed
  request; a failure offers the request details and a retry.
- Follows the shell's dark-mode setting.

## Backend endpoints

All paths are relative to the document, so they resolve under
`/collabora-wopi/`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `documents/refresh` | Rescan MinIO for documents Collabora can open |
| `GET` | `documents/` | List the documents with the Collabora URL that opens each one |
| WebSocket | `ws` | `{"type": "update"}` after every rescan |

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

Then run the view against a WOPI backend on `localhost:5000`; the dev server
proxies `/documents` and `/ws` to it:

```bash
cd services/applications/collabora/docker/wopi/files/ui
npm ci
npm run dev        # http://localhost:3000/
npm run build      # type-check, then build dist/
```

Linting and formatting use the repository-wide ESLint/Prettier setup; see
`docs/source/development_guide/code_formatting.rst`.

## Tests

A mock-backed Playwright suite in `tests/e2e`. `fixtures/mock-backend.ts`
answers the two HTTP endpoints with `page.route` and the WebSocket with
`page.routeWebSocket`, using the types from `src/api/documents.ts`.

```bash
npx playwright test
```

The suite runs on port 4313: against the dev server locally, and against a
`vite preview` of the production build in CI, where the `ui_e2e_tests` job
runs it.

| Spec | Covers |
| --- | --- |
| `boot.spec.ts` | Fresh-profile boot, dark mode from the shell |
| `list.spec.ts` | Rescan on open, sorting, search, links, empty and loading states |
| `feedback.spec.ts` | Failures, retry, rescan progress, live updates, reconnect |
| `guidelines.spec.ts` | Typeface, content width, action hierarchy, icon map |
