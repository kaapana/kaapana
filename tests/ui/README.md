# UI Tests

End-to-end tests for the Kaapana platform UI, built with [Playwright](https://playwright.dev/).

---

## Setup

```bash
cd tests/ui
npm install
npx playwright install chromium   # install the browser binary (default)
```

Testing on Firefox or Safari (WebKit) is also supported — install the binary you want and
pass `PLAYWRIGHT_BROWSER` when running (see "Quick options" below):

```bash
npx playwright install firefox webkit   # only if you plan to use them
```

Point the suite at a running Kaapana instance:

```bash
export KAAPANA_TEST_INSTANCE_UI=https://<your-instance>   # required
export NODE_TLS_REJECT_UNAUTHORIZED=0                       # required for self-signed certs
```

All other env vars are optional — the defaults match a standard local deploy:

| Variable | Default | Meaning |
|---|---|---|
| `KAAPANA_TEST_INSTANCE_UI` | `https://localhost` | Base URL of the instance |
| `KAAPANA_PROJECTS_UI_PATH` | `/projects-ui` | Project management UI path |
| `KAAPANA_WORKFLOW_UI_PATH` | `/workflow-ui` | Workflow UI path |
| `KAAPANA_EXTENSION_MGR_PATH` | `/extension-manager-ui` | Extension Manager path |

### Quick options while testing

| Option | What it does |
|---|---|
| `PLAYWRIGHT_SLOW_MO=500` (env var) | Slows down every action by that many ms, so you can actually watch what's happening — combine with `--headed` |
| `PLAYWRIGHT_BROWSER=firefox\|webkit` (env var) | Runs every suite on Firefox or Safari (WebKit) instead of the Chromium default — install the matching binary first |
| `--headed` (CLI flag) | Runs with a visible browser window instead of headless |
| `--debug` (CLI flag) | Opens the Playwright Inspector, pausing before each action so you can step through |

Example — watch a suite run step by step:

```bash
PLAYWRIGHT_SLOW_MO=500 npx playwright test --project landing-page --headed
```

Example — run the same suite on Safari instead of the default Chromium:

```bash
PLAYWRIGHT_BROWSER=webkit npx playwright test --project landing-page
```

Every suite defaults to Chromium; `PLAYWRIGHT_BROWSER` swaps the browser for *all* projects in
that run, not just one.

---

## Test Sets

Each test set maps to a subdirectory in `tests/` and runs with an authenticated Keycloak session.
All service test sets depend on `auth-setup` and reuse the saved session. (These are Playwright
"projects" under the hood — hence the `--project <name>` flag below — but "test set" is used
throughout this doc to avoid confusion with Kaapana's own project entities.)

| Test set | Folder / file | What it covers |
|---|---|---|
| `auth-setup` | `auth.setup.ts` | Logs in as `kaapana`/admin, waits for the `Project` cookie the backend needs (several APIs 401 without it), saves the session to disk |
| `landing-page` | `landing-page/` | The platform's original UI: sidebar navigation, datasets, tagging, notifications, Workflow Execution/Results, project-rights variants (no-project/non-admin user), unauthenticated state |
| `workflow-ui` | `workflow-ui/` | The `/workflow-ui` Workflows view (install a new workflow, filter/sort/search) and Runs view (submit/verify/cancel/retry, a real end-to-end run of `dummy-workflow`) |
| `project-management` | `project-management-ui/` | Project CRUD, add/remove/re-role a user, and the workflow/application whitelist rights model (Admin/PI/Scientist) |
| `system-ui` | `system-ui/` | External system pages: Airflow, Traefik, Prometheus, Grafana, Keycloak Admin |
| `extensions-ui` | `extensions-ui/` | Platform Extensions page + standalone Extension Manager UI (catalog, extensions, repositories views) |

---

## Coverage

What each test file actually does, step by step — grouped by component, collapsed by default
so you can open just the one you care about. At the end of some components there is a "Not yet covered" list.

<details>
<summary><strong>landing-page/</strong> — platform shell and data lifecycle (12 files)</summary>

#### `sidebar.spec.ts` — sidebar, header, dialogs
1. Confirm Home, Extensions, project selector, and the logo link are all visible.
2. Confirm the header buttons (About Platform, Settings, Dark Mode, Notifications) are visible.
3. Confirm the Workflows group and all its sub-links (Data Upload, Datasets, Workflow
   Execution, Workflow List, Workflow Results, Instance Overview, Active Applications) are
   visible.
4. Confirm the System, Store, Experimental, and Meta group headers are visible.
5. Confirm the Help link and its `target="_blank"`/href, and the footer Logout button.
6. Open the user menu — confirm username, "Welcome back!" subtitle, and a Log Out button.
7. Toggle Dark Mode on and back off — confirm the button's title attribute flips each time.
8. Open and close the About Platform dialog, then the Settings (Dataset Configuration) dialog.

#### `home.spec.ts` — home page
1. Confirm the logo and a "Welcome {username}!" greeting.
2. Confirm the Slack, email, and documentation cards have the right hrefs/targets; click
   Documentation and confirm the URL changes.
3. Click every workflow icon-grid card (Data Upload, Datasets, Workflow Execution, Workflows,
   Results Browser, Instance Overview, Active Applications, Extensions) and confirm each
   navigates to its route, then return home.
4. Confirm the Patients/Studies/Series dashboard counts are visible and not `N/A`.
5. Confirm at least one Apexcharts chart renders, and any visible Grafana iframes are visible.

#### `dataset.spec.ts` — dataset project isolation
1. As admin in the `admin` project, open the dataset dropdown — confirm the dataset seeded
   during setup IS visible.
2. Switch to the `public` project, open the dropdown again — confirm the same dataset is NOT
   visible.
3. Log in as a restricted (non-admin, no extra roles) user — confirm `/datasets` still loads.

#### `gallery-view.spec.ts` — datasets detail view
1. Navigate to Datasets — confirm the page renders with a Search card and either series cards
   or a modality breakdown chart.
2. Confirm a Download and/or Tag action is present somewhere on the page.

#### `tagging.spec.ts` — tag lifecycle
1. Open the `phantom` dataset, pick the first series card.
2. Create a tag, apply it to the card, confirm the card shows the tag chip.
3. Filter the gallery by that tag (add-filter → pick "Tags" → pick the tag value) — confirm
   only the tagged card shows.
4. Clear the filter, then free-text search by the tag name — confirm the card still shows.
5. Click the card again to remove the tag — confirm the chip disappears.
6. Create a second tag, enable "Multiple Tags", activate both tags in the bar, click the card
   once — confirm both chips appear together, then click again — confirm both disappear.

#### `notifications.spec.ts` — notifications
1. Open and close the Notifications dialog.
2. Create a notification via the API (no UI action does this), confirm it appears in the
   dialog, mark it read individually — confirm it disappears from the unread list.
3. Create a second notification, click "Mark all as read" — confirm it disappears too.

#### `workflow-execution.spec.ts` — DAG selector
1. Navigate to Workflow Execution — confirm the page renders.
2. Open the DAG dropdown — confirm the core `validate-dicoms` DAG is listed. This fails (not
   warns) if it's missing — that DAG ships by default on every project, so its absence means
   something is actually broken.
3. Select a DAG — confirm the Workflow name field auto-fills and Start Workflow becomes
   enabled.

#### `workflow-results.spec.ts` — Results Browser
1. Navigate to Workflow Results — confirm the results-browser heading renders.
2. Confirm a tree/list/table/empty-state element is visible.
3. Click a workflow-run folder to expand it; if a child link ends in `.html`, open it in a new
   tab.

#### `no-project-user.spec.ts` — a brand-new user with no project
1. Create a Keycloak user via the API with no project assignment.
2. Log in as that user — confirm the sidebar shows only Home and an empty Workflows group
   (no Data Upload/Datasets/etc. sub-links), and that Store/Meta/System are hidden entirely.
3. Confirm the account menu still opens and Logout is present.

#### `non-admin-project-user.spec.ts` — a plain "user"-realm-role member of a project
1. Create a project + a Keycloak user (realm role `user`), add the user to the project as
   `scientist` — all via the API.
2. Log in — confirm the project auto-selects to the one they belong to, the Workflows menu
   is present with all its sub-links *except* Instance Overview, and Store is visible.
3. Confirm System is visible (collapsed) — a project member gets that much even with no
   special AII role, unlike a no-project user where it's fully hidden. Expand it — confirm
   **Projects** is the only visible sub-link; Airflow, Kubernetes, Keycloak, Traefik,
   Jupyterlab, PACS, Prometheus, Grafana, and Documentation are all hidden.

#### `unauthenticated.spec.ts` — logged-out redirect
1. Clear cookies, visit `/` — confirm it redirects to the Keycloak login form.

#### `e2e.spec.ts` — full data lifecycle
1. Upload a generated test DICOM file via Data Upload; wait for FilePond to report "Upload
   complete".
2. Start the `import-dicoms-from-data-upload` DAG on it, confirm a success notification, and
   wait for the run to actually finish (via the Workflow List's status chips).
3. Wait for the uploaded series to appear in the `dicomupload` dataset.
4. Open the series, start the `delete-series` DAG on it, wait for that run to finish.
5. Confirm the series card is gone from the dataset.
6. Delete the dataset itself via the "Manage Datasets" dialog — confirm the success
   notification and that the dataset row disappears.
</details>

<details>
<summary><strong>workflow-ui/</strong> — the newer Workflow UI (2 files)</summary>

Split along the same line as the UI itself: `workflows.spec.ts` covers the Workflows view
(installed workflow definitions, as cards) and `workflow-runs.spec.ts` covers the Runs view
(executions of those definitions).

#### `workflows.spec.ts` — Workflows view
1. Confirm the toolbar (info, filters, refresh, sort), and that the `dummy-workflow` and
   `registration-workflow` cards specifically are present — every instance ships both by
   default, so either being missing means something's actually broken, not a valid outcome.
2. Open and close the info dialog.
3. Open the filter panel, type the first workflow's name — confirm the list narrows to it and
   a different workflow disappears; clear and close the panel.
4. Open the sort menu, switch to "Name Desc" — confirm the card order reverses; switch back.
5. Click Refresh — confirm the card count is unchanged.
6. Click START on a card — confirm the Run Workflow form opens with Expand All/Collapse All
   (or a "no configurable parameters" message), and that the Advanced panel's cleanup-policy
   dropdown offers "On success only" / "Always" / "Never". Cancel closes the form.

#### `workflows.spec.ts` — installing a new workflow, two scenarios
Both `POST /workflow-api/v1/workflows` directly — the same call the real `workflow-installer`
job makes after a Helm-chart-driven install — exercised independent of any real chart/container.

**Scenario 1 — valid metadata, invalid Airflow definition** (a placeholder string, not a real
DAG): confirms the install still succeeds (HTTP 201) and the card appears in the Workflows view
by title. Doesn't attempt to run it — with no real DAG for Airflow to sync, the card would stay
on "Not ready" indefinitely, which is expected, not a bug.

**Scenario 2 — a genuinely valid Airflow DAG, full lifecycle:**
1. Install a minimal stock-Airflow `BashOperator` DAG (no Kaapana-specific operators needed).
2. Poll until the card leaves "Checking.../Not ready" — Airflow's own scheduler scan
   (`dag_dir_list_interval`) plus workflow-api's DAG-appear wait means this can take over a
   minute; the test budgets 5 minutes total.
3. Start a real run, wait for it to reach `Completed`.
4. Delete the workflow — asserts the response is HTTP 204, then confirms the card is actually
   gone from the Workflows view afterward. This is a tested step, not silent cleanup.

Known gap: `DELETE /v1/workflows/{id}` only soft-deletes the DB row — the rendered `.py` file
is never removed from Airflow's dags folder. Accepted as minor clutter rather than giving this
test suite `kubectl`/PVC access just to clean it up.

#### `workflow-runs.spec.ts` — submit and verify a run *(serial)*
Exercises all 5 row-level actions a run can have (`WorkflowRun.vue`: Cancel, Retry, View Logs,
Download Logs, Clean):
1. Start `dummy-workflow`, capture the run-creation `POST` response — fail with the request/
   response bodies attached if it isn't HTTP 201. Confirm the run appears in the Runs view
   with a recognized status.
2. Confirm the Runs view's "Total" stat and status chips render.
3. Open View Logs on the run, confirm the log dialog opens and closes.
4. Click Download Logs — poll until it's enabled (needs at least one task_run to exist), then
   confirm a real browser download fires with a `.zip` filename.
5. Click Cancel — confirm the status chip moves to a terminal state.
6. Click Retry, capture the retry `PUT` response — fail with the response body if it isn't a
   2xx; confirm the response payload references the workflow.
7. Click Clean on the finished run — confirm the clean dialog opens and closes.

#### `workflow-runs.spec.ts` — Runs view
1. Confirm the toolbar (info, clean, refresh, search) and the info dialog.
2. Confirm the "Total" stat and status chips render, and Refresh doesn't change the total.
3. Open Clean (bulk), then Cancel out of it.
4. Open the search field's column dropdown — confirm "Status" and "Workflow" are offered; pick
   "Workflow", pick a value, apply — confirm every visible row matches; clear the filter.
5. Click a status chip — confirm the table filters to that status (when the row count matches
   the chip's label); click again to deselect.

**Not yet covered:**
- Bulk cleanup actually executing (only opening/canceling the bulk-clean dialog is tested).
- A run that genuinely errors (not just gets canceled) — status-chip and log-viewer behavior
  on a real failure.
- Retrying a run that was itself already retried (chained retries).

</details>

<details>
<summary><strong>project-management-ui/</strong> — project & user administration (6 files)</summary>

#### `project-management.spec.ts` — project CRUD *(serial, cleans up before/after)*
1. Confirm the projects list renders, the built-in `admin` project row exists, and
   "Create New Project" is visible.
2. Create a project — confirm it appears in the list (reloading if the backend reports an
   error but actually committed it).
3. Confirm a name longer than 13 characters shows "Max 13 characters" and disables Create.
4. Confirm an uppercase name shows "Only lowercase characters are supported" and disables
   Create.
5. Confirm the reserved name "admin" shows "Name \"admin\" is reserved" and disables Create.
6. Open the project's detail page — confirm the name and a "Projects" back-button render.
7. Edit the description — confirm a "Project updated successfully" notification.
8. Archive the project — confirm an "Archived" chip appears on its row; unarchive — confirm
   the chip disappears.
9. Delete the project — confirm the confirmation dialog's wording and that the row disappears.

#### `add-user-role.spec.ts` — add a user with a specific role
1. Create a scratch project and two Keycloak users (one for each role) via the API.
2. Expand "Project Users", open "Add User", search for the PI user, select them, pick the
   `principal-investigator` role card, submit — confirm they appear in the table with that
   role.
3. Repeat for the second user with the `scientist` role card.
4. Clean up: delete the scratch project and both users in `afterAll`.

#### `change-role.spec.ts` — changing a user's role changes their rights immediately
1. Create a scratch project + one user, add them as `scientist` via the API.
2. As that user: confirm "Add User" is hidden and their own row's edit/remove icons are
   disabled (no `manage_users` right).
3. Admin promotes them to `principal-investigator` via the real "Change Role" dialog.
4. As that user again: confirm "Add User" is now visible and the icons are enabled.
5. Admin demotes them back to `scientist`; confirm the rights disappear again.

#### `remove-user.spec.ts` — removing a user revokes their access
1. Create a scratch project + one `scientist` user via the API.
2. Admin removes them via the real "Remove user from project?" dialog — confirm the row
   disappears.
3. Log in as the removed user — confirm the project no longer appears in their project
   selector.

#### `workflow-whitelist.spec.ts` — the DAG/workflow whitelist, 3 roles
New projects are seeded with the *full* `default_software.json` list already whitelisted (see
the project-creation route) — restricting access means un-whitelisting a DAG, not adding one to
an empty list.
1. Create a scratch project + a PI and a scientist user, un-whitelist one DAG
   (`send-dicom`) while leaving another (`validate-dicoms`) whitelisted.
2. As PI, then as scientist: confirm the Workflow Execution DAG dropdown no longer offers the
   un-whitelisted DAG, but still offers the whitelisted one.

No admin case is asserted here: `get_allowed_software` (kaapana-backend) currently has no
admin bypass for the DAG whitelist, unlike the application whitelist below — whether that's
intentional is an open question, not something to pin a test to either way yet.

#### `app-whitelist.spec.ts` — the application whitelist, 3 roles
Unlike the DAG whitelist, `multiinstallable_whitelist` starts **empty** on a new project, and
the `can()` permission check *does* bypass for admin.
1. Create a scratch project + a PI and a scientist user; whitelist the first available
   not-yet-installed multiinstallable application (skips gracefully if the instance has none).
2. Admin: confirm Launch is enabled regardless of whitelist.
3. PI: confirm Launch is enabled only for the whitelisted app (disabled + tooltip on others).
4. Scientist: confirm Launch is disabled entirely, even for the whitelisted app (no
   `launch_application` right at all, independent of the whitelist).

**Not yet covered:**
- Accessing JupyterLab as a user in a different project — long multi-actor chain; automatable,
  but low ROI against the flake risk it'd add. Left manual for now.

</details>

<details>
<summary><strong>system-ui/</strong> — external system pages (1 file)</summary>

#### `system.spec.ts`
1. **Airflow** (`/flow/home`) — confirm the page body contains DAG-table content, or a login
   form, or general Airflow branding.
2. **Traefik** (`/traefik/dashboard/`) — confirm router/service/entrypoint content or Traefik
   branding.
3. **Prometheus** (`/prometheus/`) — confirm the expression browser, navigation, or graph UI.
4. **Grafana** (`/grafana/dashboards`) — confirm a dashboards page or a login redirect.
5. **Keycloak Admin Console** (`/auth/admin/master/console/#/kaapana`) — confirm the admin
   console (Clients/Users/Roles) or a login form.

Each check is deliberately loose -> the goal is catching a broken route,
not re-testing Airflow/Grafana/Keycloak UI themselves.

</details>

<details>
<summary><strong>extensions-ui/</strong> — Extensions & Extension Manager (2 files)</summary>

#### `extensions.spec.ts` — platform Extensions page
1. Navigate via the sidebar — confirm cards, a table, an empty-state message, or Install
   actions are present.
2. Confirm at least one card/table cell has non-empty name/description text.
3. Confirm a search/filter input is present and interactable.

#### `extension-manager.spec.ts` — standalone Extension Manager UI
1. Visiting the root URL redirects to the Catalog view.
2. Catalog lists extensions or shows an empty state, and exposes links to the Extensions and
   Repositories tabs.
3. Switching to Extensions view updates the URL and shows an installed list or empty state.
4. Switching to Repositories view updates the URL.
5. "Add Repository" opens the New Repository dialog; Cancel dismisses it.
6. Leaving the Repository URL field empty and blurring it shows "This field is required."

**Not yet covered:**
- Installing/uninstalling an extension end to end

</details>

## Running

### Step 1 — Authenticate once

```bash
npx playwright test --project auth-setup
```

Check the session file was written:

```bash
ls playwright/.auth/kaapana.json
```

### Step 2 — Run one test set at a time

```bash
npx playwright test --project landing-page
npx playwright test --project workflow-ui
npx playwright test --project project-management
npx playwright test --project system-ui
npx playwright test --project extensions-ui
```

### Step 3 — Watch a run in headed mode

```bash
PLAYWRIGHT_SLOW_MO=500 npx playwright test --project landing-page --headed
```

### Step 4 — Run the full suite

```bash
npx playwright test --project auth-setup \
  --project landing-page \
  --project workflow-ui \
  --project project-management \
  --project system-ui \
  --project extensions-ui \
  --workers 1
```

`--workers 1` avoids concurrent mutations on the same instance.

---

## Interactive UI mode

```bash
npx playwright test --ui
```

---

## Debugging a failure

```bash
npx playwright show-report
npx playwright show-trace test-results/<test-name>/trace.zip
npx playwright test --project landing-page --grep "test name" --debug
```

---

## Creating new tests

- Read the [Playwright docs](https://playwright.dev/docs/writing-tests) for basics.
- Record a test: `npx playwright codegen $KAAPANA_TEST_INSTANCE_UI`
- Always use `await page.goto('/')` — never the literal `$KAAPANA_TEST_INSTANCE_UI` string.
- Put new spec files in `tests/<subfolder>/` and they'll be picked up by the matching project.
- Each `test.describe` block must have a `beforeEach` (navigate + wait for load) and an `afterEach` (close any dialogs, restore any UI state the test may have changed).
