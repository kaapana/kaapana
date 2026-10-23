# project-management-ui

The **Projects** page of Kaapana, found under *System* in the navigation.
Admins and project managers use it to create projects and to decide, per
project, who is a member, which workflows and applications the project may
use, and which rights each project role grants.

It is a Vue 3 + Vuetify 3 + Vite app. nginx serves the built files, and the
`portal-ui` shell shows the app in an iframe under `/projects-ui`. The shell
finds the app through the `kaapana.ai/ui.*` annotations on its Ingress.

The code lives in `docker/files/src/`:

| Path | What it contains |
| --- | --- |
| `pages/index.vue` | The project list: create, edit, archive, unarchive and delete projects. |
| `pages/project.vue` | One project: its header actions and its sections for members, workflows, launchable applications and running applications. |
| `pages/role-rights.vue` | The table of which project role has which right. Only admins and project managers can open it. |
| `components/ProjectUsers.vue`, `AddUserToProject.vue` | Members: list them, add users, change a member's role, remove a member. |
| `components/ProjectWorkflows.vue` | Which workflows the project may run (its workflow whitelist). |
| `components/MultiinstallableApplications.vue`, `LaunchApplication.vue` | Applications that can be launched, their launch form, and which of them the project may use (its application whitelist). |
| `components/ActiveProjectApplications.vue`, `ApplicationParametersDialog.vue` | Applications running in the project. |
| `components/CreateNewProjectForm.vue`, `EditProjectDialog.vue` | The forms for creating and editing a project. |
| `permissions/`, `stores/policy.ts` | Decide which buttons a user sees (see *Permissions* below). |
| `stores/failureDetails.ts`, `utils/notifyFailure.ts`, `components/FailureAlert.vue` | Error messages and the dialog with the details of an error. |
| `composables/useConfirmation.ts`, `utils/projectConfirmations.ts` | The "are you sure?" questions and their texts. |
| `composables/useViewDirty.ts`, `composables/useDiscardConfirmation.ts`, `components/GuardedDialog.vue` | Unsaved changes: report them to the shell and ask before they are lost. |
| `components/ListEmptyState.vue` | What a list shows when it is empty. |
| `common/services.ts` | The HTTP clients for the backends, including the project prefix. |

## Not project-scoped

Most Kaapana pages work inside the project selected in the shell. This page
does not: it manages every project the user may see. So the shell does not
tie it to one project:

- its Ingress has no `kaapana.ai/ui.project` annotation,
- the shell loads it without a `/project/<short_id>/` prefix,
- switching projects in the shell does not reload it.

On the page of one project, calls to kube-helm and kaapana-backend still
have to say which project they are for. The clients in `common/services.ts`
put `/project/<short_id>/` of that project in front of them, and the gateway
checks the call against that project. base-ui's `httpClient` cannot do this
here, because it reads the project from the page URL, and this page's URL
has none. Calls to AII never get the prefix, because AII is not tied to a
project.

## base-ui

The app uses `@kaapana/base-ui` as it is and does not change it:

- theme, typeface, icons and dark mode: `createKaapanaVuetify`,
  `useShellSettings`, `kaapanaIcons`
- dialogs: `ConfirmDialog`, `ErrorDetailsDialog` with `apiErrorInfo`,
  `HelpIcon`
- talking to the shell: `refreshShell`, `postViewDirty`
- permission checks: `checkRoleAuthR`

Everything else lives in the app: the components listed above and
`utils/projectIcons.ts` for its own icons. Some helpers are copies of the
same files in other views, for example `notifyFailure` and the
`failureDetails` store from extensions-ui.

## Features

- **Project list**: admins and project managers see every project, everyone
  else only the projects they are a member of. Projects can be created,
  edited, archived, unarchived and deleted. Every action that deletes
  something or has wide effects asks first and says what will happen. The
  `admin` project cannot be changed.
- **Project page**: the project's external ID, description and archive
  state, and the actions for the project.
- **Archived projects**: AII refuses changes to the details, members and
  workflow whitelist of an archived project, so the page disables exactly
  these controls. Launching and uninstalling applications and the
  application whitelist keep working.
- **Members**: the members with their project role. System users are hidden
  unless asked for. Several users can be added at once with one role. A
  member's role can be changed, and a member can be removed.
- **Workflows and the application whitelist**: shown as checkboxes. Changes
  are first collected and marked on screen ("staged"), then saved or
  discarded together.
- **Applications**: launch an application with its parameter form, see the
  running ones with their parameters and links, uninstall one.
- **Role rights**: a table of roles and rights. Changes are staged and saved
  together. Rights can be added, deleted and reset to the defaults. Users
  get changed rights within a few minutes.
- **Permissions**: a button is shown only when the user may use it. Either
  the gateway's policy data allows the user's role that call, or the user
  holds the matching AII right in this project. The page has to check the
  AII rights itself because the policy data does not contain them. This
  only hides buttons. The gateway still checks every call.
- **Lists**: every list shows all its rows, shows when it is loading, and
  says whether it is empty or the search matches nothing. If loading fails,
  the list says so and offers *Details* and *Try again* instead of looking
  empty.
- **Progress**: a button shows progress while its action runs and blocks
  the actions that would conflict with it.
- **Errors**: a failed action shows a notification. Clicking it opens the
  details.
- **Unsaved changes are never lost silently**: Refresh, going to another
  page of the app and closing a dialog with changes all ask first. The page
  also tells the shell (`kaapana:view-dirty`), so the shell can ask before
  the user leaves the page.
- **Shell**: after a change to a project the page asks the shell to reload
  its project list (`kaapana:shell-refresh`).

## Backend endpoints

The page talks to three backends:

- **AII** (access-information-interface, `/aii/`): projects, members, roles,
  rights and whitelists.
- **kube-helm** (`kube-helm-api`): launches, lists and uninstalls
  applications.
- **kaapana-backend**: the list of workflows and the gateway's policy data.

kube-helm and kaapana-backend are marked for deprecation. The Extension
Manager and the Workflow, Data and Task APIs will replace them (see
`docs/source/releases.rst` and
`docs/source/concepts/platform_architecture/architecture.rst`). These do not
offer what this page needs yet, so the calls stay for now. The tables list
every call. For these two backends, the last column says why the call
stays.

### AII (`/aii/`, no project prefix)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/aii/users/current` | The current user and their realm roles. |
| GET | `/aii/aii/users/<id>/rights` | The user's AII rights per project. The double `aii` is correct: AII has its own `/aii` router below the `/aii/` ingress prefix. |
| GET | `/aii/projects` · `/aii/users/<id>/projects` | All projects (admins, project managers) or only the user's own. |
| POST · GET · PUT · DELETE | `/aii/projects` · `/aii/projects/<id>` | Create, read, edit and delete a project. |
| POST | `/aii/projects/<id>/archive` · `/unarchive` | Archive and unarchive. |
| GET | `/aii/projects/<id>/users` · `/users/<uid>/roles` | Members and their project role. |
| POST · PUT · DELETE | `/aii/projects/<id>/role/<role>/user/<uid>` · `/user/<uid>/rolemapping` | Add a member, change their role (`?role_name=`), remove them. |
| GET | `/aii/users` · `/aii/projects/roles` | Users that can be added, and the project roles. |
| GET · POST · DELETE | `/aii/projects/<id>/software-mappings` | Workflow whitelist. |
| GET · PUT | `/aii/projects/<id>/multiinstallable-whitelist` | Application whitelist. |
| GET · POST · DELETE | `/aii/projects/rights` · `/rights/<id>` · POST `/rights/reset` | The list of rights. |
| GET · POST · DELETE | `/aii/projects/roles/<rid>/rights` · `/rights/<right_id>` | Which role has which right. |

### kube-helm (`/project/<short_id>/kube-helm-api/`, marked for deprecation)

| Method | Endpoint | Purpose | Why it stays |
| --- | --- | --- | --- |
| GET | `extensions` | Applications that can be launched, and the Helm status of running ones. | The Extension Manager installs only `workflow-v1` extensions, not applications. |
| POST | `helm-install-chart` | Launch an application. | The planned Helm API does not exist yet. |
| GET | `active-applications` | Running applications, filtered to the project. | Planned for the Workflow API, not there yet. |
| POST | `helm-delete-chart` | Uninstall an application. | Same as for launching. |

### kaapana-backend (marked for deprecation)

| Method | Endpoint | Purpose | Why it stays |
| --- | --- | --- | --- |
| GET | `/project/<short_id>/kaapana-backend/client/dags?only_dag_names=true&include_all=true` | Every workflow that can go on the whitelist. | The Workflow API lists workflows, but the AII whitelist stores Airflow DAG ids, and the two are not linked. |
| GET | `/kaapana-backend/open-policy-data` (no project prefix, through base-ui) | Which role may make which call, for the permission checks. | Every view reads it this way. |

## Development

How UI views are built in general is described in
`docs/source/development_guide/preview/ui_development.rst`.

The app uses base-ui as a `file:` dependency and imports its built `dist/`.
So build base-ui first, and again after every change to its `src/`:

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build
```

Then start the app from its `docker/files`:

```bash
cd services/data-separation/project-management-ui/docker/files
npm ci
npm run dev            # http://localhost:5174/projects-ui/
```

Without a Kaapana instance behind it, every request fails; the e2e tests
below run the page against a fake backend instead. In production nginx
serves the built `dist/` on port 5000. The image builds on
a `local-only/base-ui:latest` stage (see `docker/Dockerfile`).

## Tests

The tests are Playwright end-to-end tests in `docker/files/tests/e2e`. They
run against a fake backend inside the browser, so they need no Kaapana
instance and no cluster.

- `fixtures/mock-backend.ts` answers every AII, kube-helm and
  kaapana-backend call from an in-memory copy of the test data. Changes stay
  until the test ends, so a test can check what an action changed.
- `fixtures/helpers.ts` holds the steps the tests share, for example
  `openView()` and `openProject()` to start a test and `failRoute()` to
  make a call fail.

```bash
cd services/data-separation/project-management-ui/docker/files
npx playwright test    # port 4312
```

Locally the tests run against the dev server; in CI (`ui_e2e_tests`) they
run against the production build. `npm run build` also type-checks the
tests.

| Spec | What it tests |
| --- | --- |
| `boot` | first start, dark mode and switching it, the current user or the rights failing to load |
| `projects` | the list per role, all rows, empty lists, create, edit, archive, unarchive, delete, form checks, loading and progress, the project page |
| `project-users` | members and roles, finding and adding users, changing a role, system users, archived projects |
| `project-workflows` | the workflow whitelist, staged changes and their marking, archived projects |
| `applications` | launching with parameters, uninstalling, sorting, the application whitelist and what happens if it fails to load |
| `role-rights` | who may open the page, saving and discarding the table, adding a right |
| `permissions` | which buttons admins, project managers and users with or without AII rights see |
| `confirmations` | every action that deletes something or has wide effects asks first |
| `failures` | failed loads shown in place, failed actions and their details |
| `shell` | `kaapana:view-dirty` across the sections of a page |
| `unsaved-changes` | the question before an edited dialog closes, before Refresh and before leaving the page; staged changes that survive an uninstall or a new right, and those that go with a deleted right |
| `project-scope` | the project prefix on every call that needs it, none on AII, switching projects |
| `guidelines` | the design guidelines: confirmations, theme and typeface, readable width, button hierarchy, accessible names, table markup |
