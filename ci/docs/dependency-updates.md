# Dependency updates with Renovate

[Renovate](https://docs.renovatebot.com/) is a bot that finds outdated
container images and libraries and opens merge requests to update them.

- **Config:** [`renovate.json`](../../renovate.json) in this repository.
- **Bot:** runs every hour from a separate project, see
  [Running the bot](#running-the-bot).
- **Where to look:** the GitLab issue "Dependency Dashboard (Renovate)" and
  MRs labelled `Dependencies`.

**Current state:** nothing happens without a maintainer. Renovate lists every
update on the dashboard, and an MR is only created after someone ticks its
box. Nothing is merged automatically. See [Rollout phases](#rollout-phases).

## In short: what a maintainer does

1. Open the Dependency Dashboard and tick the updates you want.
2. On the next run, Renovate opens the MR and the full pipeline runs.
3. Read the MR description. It says which tests cover each changed file.
4. If the coverage is `none`, test the component manually and note the
   result in the MR.
5. If the MR changes the `ci-base` image, bump `CI_IMAGES_TAG` in
   `.gitlab-ci.yml` on the same branch. The MR description reminds you.
6. Review and merge, or close the MR to skip that version.

## What Renovate updates

Renovate reads files through *managers*, one per file format. Only the
managers listed in `enabledManagers` run.

| Manager | Files | Examples |
| --- | --- | --- |
| `dockerfile` | every `Dockerfile` | `FROM nginxinc/nginx-unprivileged:1.31-alpine`, `FROM quay.io/keycloak/keycloak:26.6.4` |
| `gitlabci` | `.gitlab-ci.yml`, `ci/pipeline/*.yml` | `image: python:3.12`, the `docker:*-dind` services |
| `pip_requirements`, `pep621` | `requirements*.txt`, `pyproject.toml`, `constraints/*.txt`, the Airflow `constraints-*.txt` | exact `==` pins in services, `lib/*` packages |
| `npm` | `package.json` + `package-lock.json` | the Vue apps in `services/base/*-ui` |
| `maven` | `pom.xml` | the Keycloak extensions |
| `pre-commit` | `.pre-commit-config.yaml` | ruff |
| `custom.regex` | lines annotated with `# renovate:`, the opa download URL | `ARG HELM_VERSION`, `RUFF_VERSION` |
| `ansible`, `kubernetes`, `helm-requirements`, `helm-values` | `ci/ci-code/deploy/*.yaml`, `k8s/` and `manifests/` directories, Helm charts | enabled so that new files are picked up. Today they find nothing to update. |

`pre-commit` is the only manager that Renovate ships turned off. It needs
both the entry in `enabledManagers` and `"pre-commit": { "enabled": true }`.

### Security updates only

- `constraints/*.txt` holds lower bounds such as `cryptography>=46.0.5`. They
  never block an upgrade. Renovate raises a bound only when a known
  vulnerability lies below it.
- The Airflow `constraints-*.txt` is Airflow's own tested set of exact pins.
  A rule turns off its normal updates, and `vulnerabilityAlerts` turns
  security fixes back on. Other updates come with the next Airflow version,
  when the whole file is replaced.

### Not updated

| What | Why |
| --- | --- |
| `local-only/*` base images | The build creates them from this repository. They are in no registry, and the tag is always `latest`. The external image they are built on is updated instead. |
| `registry.hzdr.de/kaapana/*` images | Kaapana's own images, e.g. the patched collabora image. They follow Kaapana's rebuilds. |
| `kaapana-client`, `kaapana-containers`, `task-api` | Code from `lib/`, installed via `file://` or `git+`. A PyPI lookup would find unrelated packages. |
| Helm chart dependencies and images | All chart dependencies are local (`file://`, `0.0.0`). Image names without a tag in `values.yaml` are Kaapana images and are turned off. |
| `docker-compose` files | The manager is not enabled. They are only used for local development. |
| `templates_and_examples/`, `docs/Pipfile`, `utils/`, `rabbitmq-3.8` | In `ignorePaths`: templates, a dead Python 2 file, helper scripts and an unused image. |
| Versions in download URLs, `git clone --branch` and `pip install x==y` in Dockerfiles | Renovate cannot find them, unless they have a [`# renovate:` annotation](#annotating-a-version). This includes Airflow itself. |

`ignorePaths` replaces Renovate's default list, it does not extend it. That is
why `**/node_modules/**` is listed again, and why `tests/` is scanned.

## Merge requests and the dashboard

- **Merge requests** are labelled `Dependencies`. The title follows semantic
  commits and names the old and new version, e.g.
  `chore(deps): update dependency ruff from 0.6.4 to v0.6.9`. Grouped MRs are
  titled after the group; their versions are in the table in the MR
  description.
- **The Dependency Dashboard** is a GitLab issue labelled `Dependencies` and
  `Sprint`. It lists pending, open and closed updates, and failed lookups,
  each under its MR title. Its "Vulnerabilities" section lists the unresolved
  advisories with their severity. Subscribe to it to get notified.
- **Security fixes** get the extra label `Security` and the title
  `fix(deps): … [SECURITY] [HIGH]`, with the severity from the advisory. The
  label turns on the trivy `security_scan` job in the MR pipeline. Vulnerability data comes from
  [osv.dev](https://osv.dev) and covers PyPI, npm and Maven packages. Container
  images and GitHub releases get no security alerts, only normal updates.

### Failed pipelines and unwanted updates

- **Failed pipeline:** the MR stays open. Fix it on the Renovate branch, or
  close it. Renovate rebases open MRs on its next run, but stops once someone
  else has pushed to the branch.
- **Closed MR:** Renovate does not recreate it for the same version. For a
  major update, it skips that whole major version. The next version creates a
  new MR.
- **Failed lookup:** it shows up on the dashboard. Ignore the package with a
  `packageRules` entry that has `enabled: false`.

## Rollout phases

The approval gate is relaxed step by step. Move to the next phase when the
MRs of the current one are manageable.

| Phase | Change in `renovate.json` | What maintainers see |
| --- | --- | --- |
| 0 · Dry run | runner input `dry_run` = `full`, read-only token | nothing, the run only logs |
| **1 · Dashboard only (current)** | `dependencyDashboardApproval: true` at the top level and in `vulnerabilityAlerts` | the dashboard. An MR only after someone ticks its box. |
| 2 · Security and tested components | remove both approvals, add `dependencyDashboardApproval: true` to the `Coverage: none` rule | security MRs and MRs for tested components. Untested ones wait for approval. |
| 3 · Target state | remove the approval from the `Coverage: none` rule, optionally add a `schedule` such as `["before 6am on monday"]` | the table below |

Target state:

| Update | What Renovate does | Merge condition |
| --- | --- | --- |
| Security fix | Opens an MR right away, ignoring the schedule and the limits | Green pipeline, including trivy, and one review |
| Patch or minor | Opens grouped MRs | Green pipeline and one review |
| Patch or minor, coverage `none` | Same as above | Also a manual test, noted in the MR |
| Major | Waits on the dashboard for approval, in every phase | Same as above, plus a look at the changelog |

## Grouping and pace

- A release must be at least **3 days** old.
- At most **5** MRs are open at a time, and at most **2** are created per
  hour. Security MRs do not count.
- There is no `schedule`, so a ticked box takes effect on the next hourly run.

Patch and minor updates are grouped, one MR per group:

| Group | Contains |
| --- | --- |
| UI npm dependencies | npm in `services/base/**` |
| other npm dependencies | all other npm |
| base image Python dependencies | Python in `data-processing/base-images/**` |
| Python dependencies | all other Python |
| container base images | Dockerfile, Ansible, Kubernetes and Helm images |
| CI tooling | everything in `ci/`, `.gitlab-ci.yml`, `.pre-commit-config.yaml` |

Some versions must move together and have their own group, also for major
updates:

| Group | Contains |
| --- | --- |
| `docker engine` | the docker CLI in `ci-base` and the `docker:*-dind` images |
| `ruff` | the pre-commit hook and `RUFF_VERSION` |
| `opa` | the opa image and both opa binaries |
| `playwright` | the npm and Python packages |

Packages released together from one repository, e.g. `vue` with `@vue/*`,
stay in one MR through Renovate's default monorepo groups.

Major updates are otherwise not grouped. Security fixes always get their own
MR.

Rules in `packageRules` apply from top to bottom, and a later `groupName`
wins. That is why "UI npm dependencies" comes after "other npm dependencies".

## Test coverage

Every MR gets one `Coverage: …` label per level it touches, and one note per
changed file in its description.

| Label | Meaning | Components |
| --- | --- | --- |
| `Coverage: unit` | Unit tests run in the `tests` stage | `lib/*`, `workflow-api`, `portal-api`, `kaapana-backend`, `extension-manager-service`, `notification-service`, `auth-backend`, `keycloak-setup`, `dicom-web-filter`, `access-information-interface`, `kaapana-plugin` |
| `Coverage: e2e` | Playwright tests against a mocked backend in `ui_e2e_tests` | `base-ui` and the 10 UIs in the `ui_e2e_tests` matrix |
| `Coverage: integration` | The workflow runs in `run_workflows`. The job may fail, so check it. | processing pipelines with a `ci-config/` directory |
| `Coverage: pipeline` | The MR pipeline uses the dependency itself | `ci/`, `.gitlab-ci.yml`, `.pre-commit-config.yaml`, `tests/` |
| `Coverage: none` | Only the build and the deployment | everything else |

When a component gets tests, add its path to the matching rule in
`renovate.json`, and add it with a `!` to the `Coverage: none` rule. Keep the
two lists in sync, so that each file gets exactly one level.

### Automerge for well-tested components

Not set up yet. A `Coverage: …` label only says that tests exist, not how good
they are. Before an update merges without review, two things must hold:

- **The tests install the updated package.** Line coverage measures Kaapana
  code, not the dependency. `portal-api` has 99% coverage, but its tests
  replace `kubernetes` with a fake module and never start `uvicorn`. A
  `kubernetes` update would pass without being tested.
- **CI enforces a coverage floor**, so that the rule stays valid when tests
  shrink. Add `--cov-fail-under=<percent>` to the component's pytest job in
  `ci/pipeline/unit-tests.yml`. A failed pipeline then stops the automerge.

For each component that meets both, add a rule after the `Coverage` rules:

```jsonc
{
  "matchFileNames": ["services/base/portal-api/**"],
  "matchPackageNames": ["fastapi", "pydantic", "pydantic-settings", "httpx"],
  "matchUpdateTypes": ["patch"],
  "groupName": "portal-api tested dependencies",
  "dependencyDashboardApproval": false,
  "automerge": true
}
```

- List only packages from the component's `tests/requirements.txt`.
- Use a separate `groupName`, so that the MR only touches this component. The
  shared `Python dependencies` group spans the whole repository.
- Start with `patch`. Add `minor` after a few clean automerges.
- Renovate hands the merge to GitLab ("merge when pipeline succeeds"). Enable
  **Pipelines must succeed** in the project settings, so that GitLab never
  merges an MR whose pipeline failed or did not run.

## Where to change what

`renovate.json` accepts `//` comments, and its `packageRules` are split into
commented sections.

| To … | Change |
| --- | --- |
| stop tracking a package or file | the `Ignore` section (`enabled: false`), or `ignorePaths` for a whole directory |
| change what needs approval | `dependencyDashboardApproval` at the top, in `vulnerabilityAlerts`, or in the `Approval` section |
| bundle or split MRs | the `Groups` section |
| mark a component as tested | the `Coverage` section, see [Test coverage](#test-coverage) |
| track a version Renovate cannot find | a `# renovate:` annotation, see below |

## Annotating a version

For a version in an `ARG`/`ENV` line of a Dockerfile, or in a variable of
`ci/pipeline/*.yml`, add a comment line directly above it:

```dockerfile
# renovate: datasource=github-releases depName=helm/helm
ENV HELM_VERSION="v3.21.2"
```

```yaml
    # renovate: datasource=pypi depName=ruff
    RUFF_VERSION: "0.16.4"
```

If the value has no `v` but the release tags do, add this after `depName`:

```text
extractVersion=^v(?<version>\d+\.\d+\.\d+)$
```

`datasource` can be any
[Renovate datasource](https://docs.renovatebot.com/modules/datasource/), e.g.
`docker`, `pypi`, `npm` or `github-releases`.

The pattern is strict, and a mismatch fails silently: the dependency just
does not appear on the dashboard. Keep the order `datasource`, `depName`,
`versioning`, `extractVersion`, use single spaces, put no blank line between
comment and value, and quote YAML values. Check the dashboard after adding an
annotation.

## Running the bot

Renovate runs from the separate project
[kaapana/renovate-runner](https://codebase.helmholtz.cloud/kaapana/renovate-runner),
on the HIFIS shared runners. Its README describes the tokens, the schedule and
how to start a test run.

Lookups on github.com need a read-only github.com token in the runner
(`RENOVATE_GITHUB_COM_TOKEN`). Without it, Renovate skips these dependencies
with `github-token-required`: the ruff pre-commit hook and every
`datasource=github-releases` annotation, e.g. helm, trivy, opa, kubectl,
containerd and oauth2-proxy.

It is a separate project because the bot token can push branches, open MRs
and edit issues. In kaapana/kaapana, every job of a `develop` pipeline could
read it, including third-party code run by `npm ci` or `pip install`. In the
runner project, only the Renovate job sees it.

Other options were checked and not chosen:

- Mend's hosted Renovate app does not support self-managed GitLab.
- The DKFZ central Renovate Bot only serves DKFZ GitLab.
- Mend Renovate Community Edition is free, but not open source.
- The HIFIS Dependabot service (`hifis-bot`) needs no setup, but cannot group
  updates. With a full pipeline per MR, one MR per package is too expensive.

In kaapana/kaapana:

- Keep issues enabled, for the dashboard.
- Enable "Pipelines must succeed".
- Subscribe the maintainers to the dashboard issue.

## Testing the config locally

The local platform needs no GitLab access. It reads the files git tracks,
together with their working-tree content. An uncommitted `renovate.json` is
therefore not found as repository config. Pass it in as global config instead:

```bash
npx --yes --package renovate@44 -- renovate-config-validator --strict --no-global renovate.json

LOG_LEVEL=debug RENOVATE_CONFIG_FILE=$PWD/renovate.json RENOVATE_REQUIRE_CONFIG=optional \
  RENOVATE_ONBOARDING=false npx --yes renovate@44 --platform=local --dry-run=extract
```

- `--dry-run=extract` works offline and lists the files and dependencies it
  found.
- `--dry-run=lookup` also queries the public registries and logs the updates
  it would propose.
- Renovate needs Node 24.11 or newer.
