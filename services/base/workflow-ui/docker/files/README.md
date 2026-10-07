# workflow-ui

The Workflows V2 views on top of `workflow-api`. The platform menu shows them in the Experimental section as
**Workflows V2** (`/workflow-ui/workflows`) and **Workflow Runs V2** (`/workflow-ui/runs`).

- **Workflows:** one card per workflow with its versions. Start opens the run form with the workflow parameters and the
  cleanup policy.
- **Workflow runs:** all runs of the project with a GitLab-style query builder, cancel, retry, data cleanup, delete and
  log download. The list updates every 15 s while a run is active.
- **Logs** (`/workflow-ui/runs/<id>/logs`): the parameters one run was started with and its task logs, with search across all tasks and a severity filter.

## Shared code

The app consumes `@kaapana/base-ui` for the theme, the shared HTTP client with the project prefix, `ConfirmDialog`,
`ErrorDetailsDialog`, `HelpIcon` and the view-dirty message. See the
[UI development guide](../../../../../docs/source/development_guide/preview/ui_development.rst).

`src/utils/notify.ts` and `src/stores/failureDetails.ts` are per-view copies of the extensions-ui failure notification
pattern.

## Backends

| Backend           | Calls                                                         |
| ----------------- | ------------------------------------------------------------- |
| `workflow-api`    | Workflows, tasks, workflow runs and their actions, logs       |
| `kaapana-backend` | `GET /client/datasets` for the dataset picker of the run form |

The dataset picker is the only remaining call to the legacy kaapana-backend. data-api offers no dataset endpoint yet;
move the call there once it does.

The run actions follow the `workflow-api` contract of #2416 (`src/utils/status.ts`), which `workflow-api` does not
implement yet. Until then, delete fails on a platform, while retry and cancel of a Created run answer with the
unchanged run and have no effect. The e2e suite runs against a mock backend with these rules.

- Cancel: Created, Pending, Scheduled and Running runs.
- Retry: Error and Canceled runs that reached the engine and whose data was not cleaned. Only the failed tasks and the
  tasks after them run again.
- Cleanup: finished runs whose data was not cleaned.
- Delete: finished runs without a running cleanup. Removes the data, the engine run and the run records.

## Development

Build base-ui once and after every change to it, then work in this directory:

```sh
(cd ../../../base-ui/docker/files && npm ci && npm run build)
npm ci
npm run dev          # http://localhost:5000/workflow-ui/workflows
npm run build        # type-check and production build
```

The dev server needs the platform gateway for API calls. For a local workflow-api, use `../../docker-compose.yaml`,
which proxies `/workflow-api` to it. For in-cluster development with hot reload, see `../README.md`.

## Tests

A mock-backed Playwright suite in `tests/e2e` covers the three pages, the run form, the query builder and the design
guideline rules. It runs on port 4311 and in the `ui_e2e_tests` CI matrix.

```sh
npx playwright install chromium   # first run only
npx playwright test
```

## Format and lint

Prettier and ESLint run from the repository root, see
[Code Formatting](../../../../../docs/source/development_guide/code_formatting.rst).
