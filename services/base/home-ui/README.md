# home-ui

The Home view of the Kaapana web UI — the first page a user sees after logging
in. It is a self-contained Vue 3 / Vuetify 3 micro-frontend, served by nginx
under `/home-ui` and embedded as an iframe by the `portal-ui` shell. The shell
discovers it through the `kaapana.ai/ui.*` annotations on its ingress
(`id: home`, `default: "true"`), which make it the default view at `/`.

## Features

- **Branding header** — Kaapana logo, optionally a second (project/deployment)
  logo and tagline, plus links to the Kaapana website, Slack, documentation and
  support email. Override the branding per deployment via the chart's
  `branding:` values block, which mounts a ConfigMap over the app's default
  `branding.json`.
- **Greeting** — time-of-day greeting for the logged-in user and the currently
  selected project.
- **Capabilities** — a card per capability (Data Upload, Datasets,
  Workflow Execution, Workflow List, Results, Tasks, Apps, Extensions), each a
  shortcut into that view. Deliberately unordered: they are entry points, not
  steps in a sequence. Capabilities a user's role may not access stay visible
  but dimmed. Clicking one posts `kaapana:navigate` to the shell
  (`navigateShell` from `@kaapana/base-ui`) rather than navigating the top
  window, so the shell applies its unsaved-changes guard and reports an
  unavailable view instead of silently bouncing home.
- **Utilization** — live CPU, memory, network, and (if the platform has
  `gpu_support`) GPU graphs, polled every 15 s through the kaapana-backend
  Prometheus passthrough with client-side sparkline history. Degrades to a
  "Monitoring data not available" note when Prometheus is unreachable.
- **Data** — platform-wide patient/study/series totals, then the user's project
  list with per-project counts and the caller's role, plus an on-demand detail
  dialog with histogram charts for the current project. Selecting another
  project posts `kaapana:project-switch` to the shell (`switchProject` from
  `@kaapana/base-ui`), which swaps the URL prefix without reloading itself;
  served standalone it falls back to navigating this document.
- **Notifications** — live notification feed (websocket) with unread count and
  pagination; rows are title-only and open a detail dialog carrying the full
  body and a mark-as-read action.

The view reacts to the shell: dark-mode changes apply instantly and a project
or settings switch remounts the page (both signalled via same-origin
`localStorage` `storage` events written by `portal-ui`).

## Layout

```
home-ui/
├── docker/
│   ├── Dockerfile            # 3-stage: base-ui lib → node build → nginx-unprivileged (port 5000)
│   └── files/                # the Vite app
│       ├── src/
│       │   ├── api/          # typed backend clients (badges, dashboard, monitoring, notifications)
│       │   ├── stores/       # Pinia stores (metrics, notifications, commonData/OPA)
│       │   ├── components/   # the page building blocks
│       │   └── views/Home.vue
│       ├── public/branding.json
│       └── tests/e2e/        # mock-backed Playwright suite
└── home-ui-chart/            # Helm chart (Deployment, Service, Ingress /home-ui, branding ConfigMap)
```

## Run locally

Auth, the `httpClient` (project scoping), the project store, the Vuetify theme
and the shell-settings sync all come from `@kaapana/base-ui`, a `file:`
dependency consumed as its built `dist/` — build the library first, and re-build
it after any change to its `src/` (consumers otherwise import the stale `dist/`
through the npm symlink and nothing errors, the change is just missing):

```bash
cd services/base/base-ui/docker/files
npm ci
npm run build
```

Then run this view:

```bash
cd services/base/home-ui/docker/files
npm ci
npm run dev        # http://localhost:5000/home-ui/
```

Without a running platform, backend calls fail and the page renders its
degraded states — layout and branding are still reviewable. In dev mode auth
falls back to `/jsons/testingAuthenticationToken.json` instead of
`/oauth2/userinfo`. Shell state (dark mode) is read from
`localStorage["settings"]`, which the `portal-ui` shell seeds in production; the
selected project comes from the document URL, so serve the app under
`http://localhost:5000/project/<short_id>/home-ui/` to work in a project;
served without the prefix (`/home-ui/`), the project store redirects onto the
user's first project.

## Test locally

Mock-backed Playwright suite (no platform required, port **4305**):

```bash
cd services/base/home-ui/docker/files
npm run test:e2e                                  # dev server + html report
npx playwright test --ui                          # interactive debugging
CI=1 npm run build && CI=1 npx playwright test    # what CI runs (preview + junit)
```

All backend traffic is stubbed via route interception in
`tests/e2e/fixtures/mock-backend.ts`. CI runs the suite in the `ui_e2e_tests`
job (`ci/pipeline/unit-tests.yml`), matrix entry `home-ui`.

## Required endpoints

All endpoints are same-origin behind Traefik. Project scoping happens
server-side: project-scoped calls carry the `/project/<short_id>` prefix of the
document URL (added by the shared `httpClient` for
`^/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)/`), which
auth-backend authorizes and turns into a `Project` header, so the dataset
endpoints only ever see that project. `/aii/…` and `/notifications/…` are not
project-prefixed.

| Endpoint | Used for | Required |
|---|---|---|
| `GET /oauth2/userinfo` | logged-in user (JWT) | yes |
| `GET /kaapana-backend/open-policy-data` | OPA gating of links/steps | yes (links hidden without it) |
| `GET /aii/users/current` | AII user id + realm roles | yes |
| `GET /aii/projects`, `GET /aii/users/{id}/projects` | project list | yes |
| `POST /kaapana-backend/dataset/dashboard` | patient/study/series stats + histograms | optional (stats show N/A) |
| `GET /kaapana-backend/monitoring/query/{name}?q=<promql>` | CPU/mem/net/GPU utilization + platform totals | optional (panel degrades) |
| `GET /kaapana-backend/monitoring/query-range/{name}?q=<promql>&minutes=&step=` | one-off sparkline backfill per utilization metric | optional (sparklines start empty and fill from the live poll) |
| `GET /kube-helm-api/pending-applications-count` | Tasks-card badge count (15 s poll) | optional (badge absent / last known) |
| `GET /notifications/v2/`, `PUT /notifications/v2/{id}/read` | notification feed | optional (empty state) |
| `WS /notifications/ws` | live notification updates | optional |

## Build / deploy

Image `home-ui` (label in `docker/Dockerfile`), chart `home-ui` — a dependency
of the platform chart's `services-namespace`
(`platforms/kaapana-platform-chart/deps/services-namespace/requirements.yaml`).
Deployment branding example:

```yaml
# home-ui chart values
branding:
  enabled: true
  logoUrl: /assets/img/my-clinic.png   # any browser-reachable image URL
  title: My Clinic
  text: Radiology research platform
```
