# Kaapana CI

How to start a pipeline and choose what it runs.

| Doc | Read it when |
|---|---|
| [glab.md](docs/glab.md) | you want to start and inspect runs from the terminal, or a ready-made recipe |
| [local-ci.md](docs/local-ci.md) | you want the jobs, or the deployment, on your own machine |
| [internals.md](docs/internals.md) | how the pipeline works: stages, templates, runners scaling, registry switch, the ci-base image |
| [troubleshooting.md](docs/troubleshooting.md) | a job failed - common causes|

Pipeline configuration is [`.gitlab-ci.yml`](../.gitlab-ci.yml) plus stage files under [`ci/pipeline/`](pipeline/).

## Starting a pipeline

### Automatic triggers

| Trigger | Configuration |
|---|---|
| Merge request | Full pipeline on every push to the branch with default configuration. A draft MR (Draft, WIP) runs nothing. Label the MR `Security` for security scan, or `CI` for CI tests |
| Push to `develop` | Full pipeline|
| Schedule | Full pipeline with the schedule's own configuration ([below](#scheduled-pipelines)) |
| Protected tag `X.Y.Z` | Release build against the release registry ([internals.md](docs/internals.md#registries)) |


### Manually triggered

| Trigger | Configuration |
|---|---|
| MR → **Pipelines** → **Run pipeline** | a re-run of the MR pipeline on the current head, defaults |
| MR → **Pipelines** → **Run pipeline > Run with modified values** | a re-run of the MR pipeline on the current head with modified values form |
| **Build → Pipelines → Run pipeline** | a form with pre-defined configuration. 
| `glab ci run` | API trigger from the terminal, scriptable and repeatable ([glab.md](docs/glab.md)) |
| gitlab-ci-local | the job *scripts* in docker on your machine, no pipeline ([local-ci.md](docs/local-ci.md#scenario-3-run-jobs-without-gitlab)) |

## Pausing all CI: `MAINTENANCE`

Set the project variable `MAINTENANCE=true` (Settings → CI/CD → Variables) and
no MR, push or schedule pipeline is created any more. Web, API and trigger runs
still start, and so do release tags, so you can keep testing while the fleet is
down. Set it back to `false` to resume.

## Scheduled pipelines

[Build → Pipeline schedules](https://codebase.helmholtz.cloud/kaapana/kaapana/-/pipeline_schedules).

| Schedule | Ref | Purpose |
|---|---|---|
| `develop` | `develop` | nightly full run |
| `Build from scratch to determine issues with external resources` | `develop` | catch broken external downloads |
| `Build latest release` | latest release tag | prove the release still builds from scratch |

## Runners

Four Harvester VMs, one runner each: `tests-runner`, `build-runner`,
`security-runner`, `deploy-runner`. Point a stage at your own machine with a
`*_runner_tag` input ([local-ci.md](docs/local-ci.md#scenario-1-run-the-jobs-on-your-machine)).

## Lint and the pre-commit hook

Ruff, the pre-commit hook and the local commands are in the development guide:
[Code Formatting](../docs/source/development_guide/code_formatting.rst).
The CI-specific parts:

| Config | Ruleset | Used by |
|---|---|---|
| [`ruff.toml`](../ruff.toml) | enforced: `E4`, `E7`, `E9`, `F`, `I`, 120 columns | pre-commit, and the `lint` job |
| [`ci/ruff-quality.toml`](ruff-quality.toml) | advisory: adds `B`, `C4`, `SIM`, `UP`, `RUF`, `W` | the `code_quality` job only |

Both jobs are in [`ci/pipeline/lint.yml`](pipeline/lint.yml) and neither blocks
a merge: `lint` is `allow_failure: true`, `code_quality` always exits zero and
only publishes the report.

## Configuration reference

Four groups of knobs. Two are **inputs** and two are **variables**

### 1. `*_runner_tag` inputs — where a stage runs

One per stage group. Point a stage at your own machine by giving your runner's
tag ([local-ci.md](docs/local-ci.md#scenario-1-run-the-jobs-on-your-machine)).

| Input | Default | Runs |
|---|---|---|
| `tests_runner_tag` | `tests-runner` | preflight and the tests stage |
| `build_runner_tag` | `build-runner` | the ci-image and build stages |
| `security_runner_tag` | `security-runner` | the security stage |
| `deploy_runner_tag` | `deploy-runner` | deploy, integration tests and clean |

### 2. `exec_*` inputs — what runs

Every stage toggle. Grouped as `[exec]` in the run form.

| Input | Default | Meaning |
|---|---|---|
| `exec_unit_tests` | `true` | tests stage: unit tests + documentation build |
| `exec_lint` | `true` | tests stage: ruff check + code quality report |
| `exec_build` | `true` | build stage: full platform build |
| `exec_security_scan` | `false` | trivy scan of the images this commit resolves to. A failed scan still publishes what it managed to check |
| `exec_deploy` | `true` | deploy stage: deployment VM/target + platform installation |
| `exec_server_installation` | `true` | `true` installs microk8s and helm on the target (needs passwordless sudo). `false` assumes a prepared target and checks it read-only |
| `exec_redeploy` | `false` | `false` makes an already-deployed platform a fatal check; `true` undeploys it first |
| `exec_integration_tests` | `true` | test stage: pytest + Playwright against the deployed platform |
| `exec_integration_test_jobs` | `""` | comma-separated allowlist of integration-test jobs (`scan_ports`, `first_login`, `install_extensions`, `send_data`, `run_workflows`). Empty runs all of them; |
| `exec_destroy_delayed` | `false` | keep the deployment VM for 4 h after the pipeline |

### 3. `DEPLOYMENT_INSTANCE_*` variables — the target

Where the platform gets deployed and what the VM looks like. Leave
`DEPLOYMENT_INSTANCE_FQDN` empty and the pipeline provisions a throwaway
Harvester VM from the rest of these; set it and every `_VM_`/Harvester value
below is ignored.

| Variable | Default | Meaning |
|---|---|---|
| `DEPLOYMENT_INSTANCE_FQDN` | *empty* | Deploy onto this host and never destroy it. Empty provisions a fresh VM. Max 57 characters (`dcmsend` peerhost limit) and it must resolve *inside the job container* |
| `DEPLOYMENT_INSTANCE_USER` | `ubuntu` | SSH user on the target |
`DEPLOYMENT_INSTANCE_SSH_KEY` | None | SSH private key file-variable

### 4. `CI_EXEC_*` variables — build and scan arguments

Free-form flag strings handed straight to `kaapana-build`. Build arguments like --latest are cross-used in scanning job, therefore left as a VARIABLE

| Variable | Default | Meaning |
|---|---|---|
| `CI_EXEC_BUILD_ARGUMENTS` | `"--cache-from -pp 8 --keep-buildx-builder"` | extra `kaapana-build` flags for `build_packages`, e.g. `--build-only`, `--cache-from`. |
| `CI_EXEC_SECURITY_SCAN_ARGUMENTS` | `--vulnerability-scan --offline-packages-scan --configuration-check --create-sboms` | flags for `security_scan` |
| `CI_EXEC_DOCKER_PRUNE` | `false` | `true` wipes the build runner's docker cache before the build (cold build) |
