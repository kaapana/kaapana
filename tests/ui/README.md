# UI Tests

## Setup

```bash
cd tests/ui
npm install
export KAAPANA_TEST_INSTANCE_UI=https://<your-instance>   # required
export KAAPANA_PROJECTS_UI_PATH=/projects-ui               # optional, this is the default
```

## Test projects

| Project | What it covers | Auth |
|---|---|---|
| `first-login` | Changes the default `kaapana` password to `admin` on a fresh instance | none |
| `auth-setup` | Logs in as `kaapana`/`admin` and saves the session to `playwright/.auth/` | none (creates it) |
| `project-management` | Full CRUD lifecycle of the project-management-ui (`/projects-ui`) | saved session |
| `chromium` / `firefox` / `webkit` | All other spec files on three desktop browsers | none |

## Running locally

### Full suite (fresh instance where first-login hasn't been done yet)
```bash
npx playwright test
```

### Against an already-configured instance (password already `admin`)
Skip `first-login` — run the setup and feature tests directly:
```bash
npx playwright test --project auth-setup --project project-management --workers 1
```

### Only project-management tests (auth-setup runs automatically as a dependency)
```bash
npx playwright test --project project-management
```

### Interactive UI mode
```bash
npx playwright test --ui
```

### View the last HTML report
```bash
npx playwright show-report
```

### View a trace from a failed test
```bash
npx playwright show-trace test-results/<test-name>/trace.zip
```

## On failure

Failed tests automatically save:
- **Screenshot** — `test-results/<name>/test-failed-*.png`
- **Video** — `test-results/<name>/video.webm`
- **Trace** — `test-results/<name>/trace.zip` (open with `npx playwright show-trace` or upload to https://trace.playwright.dev)

## In CI

The `playwright_ui_tests` GitLab CI job runs after `first_login` completes. It skips the
playwright `first-login` project (the pytest job already handled password setup) and runs:

```bash
npx playwright test --project auth-setup --project project-management --workers 1
```

Artifacts (`playwright-report/` and `test-results/`) are uploaded to GitLab and exposed as
**"Playwright UI Report"** in the pipeline sidebar. The JUnit XML is reported as test results
in the pipeline view.

## Creating new tests

- Read the [Playwright docs](https://playwright.dev/docs/writing-tests) for basics.
- Record a test: `npx playwright codegen $KAAPANA_TEST_INSTANCE_UI`
- In VS Code: install the **Playwright Test for VS Code** extension and use "Record new".
- Always use `await page.goto('/')` (not the literal `$KAAPANA_TEST_INSTANCE_UI` string) so the
  `baseURL` from the config is picked up.
- Tests for the project-management-ui belong in `tests/project-management.spec.ts` and should
  navigate directly to `KAAPANA_PROJECTS_UI_PATH` rather than going through the portal nav.
