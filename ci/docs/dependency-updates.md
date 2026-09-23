# Dependency updates with Renovate

[Renovate](https://docs.renovatebot.com/) opens merge requests that update
container images and libraries. The repository config is
[`renovate.json`](../../renovate.json). The bot runs separately and uses this
config (see [Running the bot](#running-the-bot)).

## What Renovate updates

| Manager | Files | Examples |
| --- | --- | --- |
| `dockerfile` | every `Dockerfile` | `FROM nginxinc/nginx-unprivileged:1.31-alpine`, `FROM quay.io/keycloak/keycloak:26.6.4` |
| `gitlabci` | `.gitlab-ci.yml`, `ci/pipeline/*.yml` | `image: python:3.12`, the `docker:*-dind` services |
| `pip_requirements`, `pep621` | `requirements*.txt`, `pyproject.toml` | exact `==` pins in services, `lib/*` packages |
| `npm` | `package.json` + `package-lock.json` | the Vue apps in `services/base/*-ui` |
| `maven` | `pom.xml` | the Keycloak extensions |
| `pre-commit` | `.pre-commit-config.yaml` | ruff |
| `custom.regex` | lines annotated with `# renovate:` | `ARG HELM_VERSION`, `RUFF_VERSION`, the opa download URL |

Renovate does not touch these:

- `local-only/*` base images. The build creates them from this repository.
  Their tag is always `latest`.
- Helm charts. All chart dependencies are local (`file://`, `0.0.0`), and all
  chart images are built by Kaapana.
- `constraints/`. These files are hand-curated security floors.
- The Airflow constraints file. It is replaced as a whole when Airflow is
  updated.
- `templates_and_examples/`, `docs/Pipfile`, `utils/internet-benchmark/` and
  the unused `rabbitmq-3.8` image.
- The dev-only `docker-compose` files.
- Git references to this repository, e.g. `kaapana-client@git+…`.
- Versions in download URLs and `git clone --branch`, unless they have a
  `# renovate:` annotation.

## How updates are communicated

- **Merge requests**, labelled `Dependencies`. Every MR states the test
  coverage of each changed file (see [below](#test-coverage)).
- **Dependency Dashboard**, a GitLab issue named "Dependency Dashboard
  (Renovate)". It lists open, pending and failed updates. Major updates wait
  there for approval. Subscribe to the issue to get notified.
- **Security updates** get the additional label `Security`. That label also
  turns on the trivy `security_scan` job in the MR pipeline.

## The process

| Update | What Renovate does | Merge condition |
| --- | --- | --- |
| Security fix | Opens an MR right away, outside the schedule and the limits | Green pipeline, including the trivy scan, and one review |
| Patch or minor | Opens grouped MRs on Monday morning | Green pipeline and one review |
| Patch or minor in a component with coverage `none` | Same as above | Also a manual test, with the result written in the MR |
| Major | Lists it on the dashboard. A maintainer ticks the box to create the MR. | Same as above, plus a look at the changelog |

This table is the target state. The rollout starts stricter, see
[Rollout phases](#rollout-phases).

Nothing is merged automatically. Every MR runs the full pipeline, and a
maintainer reviews it.

Automated steps:

- detecting new versions and security fixes
- creating and rebasing the MR branches
- updating the lock files
- running the pipeline

Manual steps:

- approving major updates on the dashboard
- reviewing and merging
- manual tests for untested components
- bumping `CI_IMAGES_TAG` when an MR changes the `ci-base` image. The MR
  description says so.

### Failed pipelines and unwanted updates

- **Failed pipeline:** the MR stays open. Either fix it on the Renovate
  branch, or close it. Renovate rebases open MRs on its next run. It stops
  doing so once someone else has pushed to the branch.
- **Closed MR:** Renovate does not recreate it for the same version. For a
  major update, it ignores that whole major version. The dashboard lists it
  under "closed". The next version creates a new MR.
- **Unsupported dependency:** a lookup that fails shows up on the dashboard.
  Ignore the package with a `packageRules` entry that has `enabled: false`.

### Rollout phases

| Phase | Setting | What maintainers see |
| --- | --- | --- |
| 0 · Dry run | `RENOVATE_DRY_RUN=full` and a read-only token in the runner project | nothing; the run only logs what it would do |
| 1 · Dashboard only | `dependencyDashboardApproval: true` at the top level and in `vulnerabilityAlerts` | the dashboard issue; an MR only after someone ticks its box |
| 2 · Security and tested components | remove the approval at the top level and in `vulnerabilityAlerts`; add `dependencyDashboardApproval: true` to the `Coverage: none` rule | security MRs and grouped MRs for tested components; untested ones wait for approval |
| 3 · Target state | remove the approval from the `Coverage: none` rule; optionally add a `schedule` such as `["before 6am on monday"]` | the process table above |

`renovate.json` currently implements phase 1. Move to the next phase when
the MRs of the current one are manageable.

### Grouping and pace

The bot runs every hour. A release must be at least 3 days old. At most 5 MRs
are open at the same time, and at most 2 are created per hour. There is no
`schedule` yet, so a ticked dashboard box takes effect on the next run.

Patch and minor updates are grouped, so a group lands in one MR:

- UI npm dependencies (`services/base/**`)
- other npm dependencies
- base image Python dependencies
- Python dependencies (everything else)
- container base images
- CI tooling

Renovate's default monorepo groups (`group:monorepos`) are turned off. They
would take `vue` and `@playwright/test` out of the groups above.

Major updates are not grouped. Security fixes always get their own MR.

Some versions must move together. Each of these sets has its own group:

- `docker engine`: the docker CLI in `ci-base` and the `docker:*-dind` images
- `ruff`: pre-commit and `RUFF_VERSION`
- `opa`: the opa image and both opa binaries
- `playwright`: the npm and Python packages

## Test coverage

Every MR gets one `Coverage: …` label per level it touches. Its description
has one note per changed file.

| Label | Meaning | Components |
| --- | --- | --- |
| `Coverage: unit` | Unit tests run in the `tests` stage | `lib/*`, `workflow-api`, `portal-api`, `kaapana-backend`, `extension-manager-service`, `notification-service`, `auth-backend`, `keycloak-setup`, `dicom-web-filter`, `access-information-interface`, `kaapana-plugin` |
| `Coverage: e2e` | Mock-backed Playwright tests in `ui_e2e_tests` | `base-ui` and the 10 UIs in the `ui_e2e_tests` matrix |
| `Coverage: integration` | The workflow runs in `run_workflows` (allowed to fail) | processing pipelines with a `ci-config/` directory |
| `Coverage: pipeline` | The MR pipeline uses the dependency itself | `ci/`, `.gitlab-ci.yml`, `.pre-commit-config.yaml`, `tests/` |
| `Coverage: none` | Only the build and the deployment | everything else |

When a component gets tests, add its path to the matching rule in
`renovate.json`. Also add it with a `!` to the `Coverage: none` rule. The two
lists must stay in sync, so that each file gets exactly one level.

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

If the value has no `v` but the release tags do, add the following after
`depName` to strip the `v`:

```text
extractVersion=^v(?<version>\d+\.\d+\.\d+)$
```

`datasource` can be any
[Renovate datasource](https://docs.renovatebot.com/modules/datasource/), e.g.
`docker`, `pypi`, `npm` or `github-releases`.

## Running the bot

Renovate runs from the separate project
[kaapana/renovate-runner](https://codebase.helmholtz.cloud/kaapana/renovate-runner),
on the HIFIS shared runners. Its README describes the tokens, the schedule and
how to start a test run.

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
together with the working-tree content. An uncommitted `renovate.json` is
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
