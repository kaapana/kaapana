# How the Kaapana CI works

What the pipeline is made of, how the pieces hand work to each other, and what
to touch when you extend it.

Starting a run and configuring one: [ci/README.md](../README.md). 

Running jobs
or the deployment on your own machine: [local-ci.md](local-ci.md).

## Anatomy of a run

Test the code → build the platform images → deploy them on a fresh throwaway VM
→ test that live deployment → delete the VM.

| Stage | Jobs | Runs on | Duration |
|---|---|---|---|
| `preflight` | `preflight_variables`, `preflight_target`, `build_ci_image` | tests / build runner | seconds |
| `tests` | ~20 unit-test jobs, the UI matrix, docs build, lint | tests runner | minutes |
| `build` | `build_packages` | build runner | hours (much less with a warm cache) |
| `security` | `security_scan` | security runner | hours |
| `deploy` | `prepare_deployment` → `server_installation` → `platform_deployment` | deploy runner, ansible over SSH | ~1 h |
| `test` | `setup_integration_tests`, `scan_ports`, `first_login`, `install_extensions`, `send_data`, `run_workflows`, `playwright_ui_tests` | deploy runner, against the live platform | 1–3 h |
| `clean` | `destroy_deployment`, `if_ci_failing` | deploy runner | minutes |

Three properties the design leans on:

- **Every job runs in a fresh container.** Nothing persists on the machines;
  credentials arrive as File-type CI variables and die with the job.
- **The registry is the only handoff between build, deploy and security scans.**
  All three derive the same tag from `git describe`, and all three read
  `--latest` out of `CI_EXEC_BUILD_ARGUMENTS`.
- **The deployment VM is disposable.** `destroy_deployment` deletes it even after a
  failure — except a deploy target given by FQDN, which is never destroyed.

## Configuration layout

[`.gitlab-ci.yml`](../../.gitlab-ci.yml) holds:

1. `spec:inputs` — the stage toggles and runner tags: type, default, description
2. `workflow:rules` — which pipelines exist at all
3. global `variables:` — registries, proxy, deployment defaults, `CI_IMAGES_TAG`,
   and the two `kaapana-build` argument strings
4. the `include:` list, which passes inputs down per stage file

Each stage file under [`ci/pipeline/`](../pipeline/) declares its own
`spec:inputs` and reads them as `$[[ inputs.name ]]`. That is a compile-time
substitution, not a variable: it resolves when the pipeline is created, so it
works in `rules:` and `tags:`, where a variable would not.


## Stage by stage

Every stage file opens with a header stating what the stage takes in and hands
out. An MR that adds a dependency between stages extends that header.

### preflight

`preflight_variables` runs on every pipeline, needs no checkout
(`GIT_STRATEGY: none`) and fails in seconds naming what is missing. It checks
only what the *enabled* stages need, and prints variable names, never values.
Beyond emptiness it catches:

- `CI_REGISTRY_USER` equal to `gitlab-ci-token` — the project variable was
  deleted and jobs silently got GitLab's predefined value
- a `DOCKER_AUTH_CONFIG` with no entry for the `CI_REGISTRY_URL` host
- `DOCKER_IO_USER` set with an empty `DOCKER_IO_PASSWORD`
- a release tag pipeline without the `RELEASE_REGISTRY_*` triple
- `DEPLOYMENT_INSTANCE_FQDN` over 57 characters — `dcmsend` rejects longer
  peerhosts, and `prepare_deployment` would only notice after the build
- deploy enabled without `DEPLOYMENT_INSTANCE_SSH_KEY`, or without
  `HARVESTER_KUBECONFIG` when a VM has to be provisioned

`preflight_target` runs only when a target is given by FQDN It runs
[`target_readiness.yaml`](../ci-code/deploy/target_readiness.yaml) over SSH,
read-only and without sudo. `after_script` prints the check table, so it appears
even when the playbook failed; there is no artifact.

`build_ci_image` rebuilds `ci-base` on change. Restricted to MR and `develop` push pipelines.

### tests

Around twenty jobs extending `.test_template`: `python:3.12`, a **5-minute
timeout**, and a shared pip cache (`key: pip-test-jobs`).

`build_documentation` uploads the built HTML and its log. `check_readthedocs`
runs only on scheduled `develop` pipelines. 

`lint` and `code_quality`

### build

`build_packages` is one job, up to 8 hours (`timeout` **and**
`RUNNER_SCRIPT_TIMEOUT`, which the runner enforces separately).

It extends `.build_cli_env`, shared with `security_scan`: `ci-base`,
`environment: name: $REGISTRY_ENV` for the registry credentials, a full clone
with tags (`GIT_STRATEGY: clone`, `GIT_DEPTH: 0`) because `kaapana-build` derives
its version tag from `git describe`, and a checkout that reconstructs a branch
ref — MR pipelines check out a detached `CI_COMMIT_SHA`.

The script unsets `DOCKER_AUTH_CONFIG` (docker ≥ 28 would let it override the
`docker login` that follows), logs into the registry and optionally docker.io,
prunes when asked, and runs `kaapana-build`. `build.log` is uploaded pass or
fail.

The docker CLI talks to the **host** daemon through a socket mount on the build
runner, which is what keeps the layer cache warm across pipelines.

### security

`security_scan` runs `kaapana-build --scan-only`, so the scan, the consolidation
and the report writing all happen inside `build_cli`'s `SecurityScanner` — the
job only calls it, and the same command reproduces everything locally. It needs
no build in the same pipeline: with `exec_build:false` it scans whatever tag this
commit already resolves to.

Its flags come from `CI_EXEC_SECURITY_SCAN_ARGUMENTS`, and it reads
`CI_EXEC_BUILD_ARGUMENTS` for `--latest` as well: the scan pulls the tags
`build_packages` pushed, so it has to derive them the same way.

The trivy DB is cached per runner (`key: trivy-db`). Reports land in `reports/`
and are kept forever:

| File | Produced when |
|---|---|
| `consolidated_vulnerability_scan.json` | `--vulnerability-scan` / `--offline-packages-scan` |
| `interactive_report.html` | same |
| `gl-container-scanning-report.json` | same — this is what GitLab's security widget reads |
| `consolidated_misconfiguration_check.json` | `--configuration-check` |
| `consolidated_sbom.json` | `--create-sboms` |

The consolidated JSON is fetchable straight from the artifacts API, e.g. for a dashboard polling nightly run:

```
GET /api/v4/projects/:id/jobs/artifacts/:ref_name/raw/reports/consolidated_vulnerability_scan.json?job=security_scan
```

Coverage is container images plus the offline installer's bundled snap packages,
which is why `ci-base` carries snapd and squashfs-tools.

### deploy

Three jobs, all extending `.remote_execution_template` (`ci-base`, ansible
settings, `chmod 600` on the SSH key).

**`prepare_deployment`** resolves the version once for the whole pipeline:
`git describe --tags --always`, rewritten to `X.Y.Z-latest` when
`CI_EXEC_BUILD_ARGUMENTS` contains `--latest` — everything before the first
`-`, the rule `build_cli` applies. It then asks the registry whether
`kaapana-admin-chart` exists at that version and fails if not — deliberately
before any VM is created. Only then does it provision a Harvester VM or accept
`DEPLOYMENT_INSTANCE_FQDN` as the target, and write `artifacts/deployment.env`.

It is `interruptible: false`, so a newer pipeline cannot auto-cancel a run that
already owns a VM. The whole pipeline is non-interruptible from this point.

**`server_installation`** is the only job needing sudo on the target. It installs
microk8s and helm and raises kernel limits. `exec_server_installation:false`
skips it for prepared targets.

**`platform_deployment`** optionally undeploys first (`CI_EXEC_REDEPLOY`), then
runs `deploy_platform.yaml`. Artifacts: `deployment.log` (ending with the
Keycloak admin password), `undeploy.log`, `system_check.log` listing every
resource and its health, and a small `deployment.html` exposed as the deployment
report.

Depending on `CI_EXEC_REDEPLOY` and `CI_EXEC_SERVER_INSTALLATION` values, preflight target changes behaviour.

### integration tests

`setup_integration_tests` extracts `CLIENT_SECRET` from the running platform and
passes it on as a dotenv artifact. Everything after it extends
`.integration_test_local`: `pip install --no-deps -e` the repo's test package
(the dependencies are already baked into `ci-base`, so only the current code is
registered), then pytest against `--host $VM_FQDN`.

| Job | Notes |
|---|---|
| `scan_ports` | nmap against the target; `--allowed-ports 22,80,443` |
| `first_login` | Keycloak login; admin password change; the rest of the chain assumes it worked |
| `install_extensions` | 4 xdist workers, `retry: 2` |
| `send_data` | DICOM upload, serial (`PYTEST_WORKERS: 0`), `retry: 2`; test data cached in `/data` on the deploy runner |
| `run_workflows` | 2-hour timeout, `allow_failure: true`, `PYTEST_DIST: loadgroup` ([below](#workflow-testcases-ci-config)) |
| `playwright_ui_tests` | node + chromium from `ci-base`, one worker, `auth-setup` and `project-management` projects; publishes the Playwright HTML report |

`exec_integration_test_jobs` narrows this set. Each job carries a rule that
turns it off when the input is non-empty and does not name it, so the default
`""` runs everything. Useful for target deployment where `first_login` should be skipped.

### clean

`destroy_deployment`'s `needs:` list **is the teardown barrier**: with
`when: always` the job starts once every listed job is terminal. Any job that
touches the test VM has to appear there, `optional: true` so reduced pipeline
shapes stay valid. Its rules, in order: never when the target came from
`DEPLOYMENT_INSTANCE_FQDN`; delayed by 4 hours when `exec_destroy_delayed`;
otherwise always.

`if_ci_failing` runs on `develop` failures only (never for FQDN targets). It
needs *every* job in the pipeline, because `when: on_failure` watches only the
jobs it needs. `artifacts: true` marks the jobs whose logs are attached to the
ticket it opens — never set that on a job whose artifacts contain secrets. It
then posts to Slack.

## What passes between jobs

| Handoff | Carrier |
|---|---|
| built images and charts | the registry, tagged with `git describe` of the commit |
| where the test system is | `artifacts/deployment.env` (dotenv: `VM_FQDN`, `VM_USER`, `VERSION_TAG`), with `DEPLOYMENT_INSTANCE_*` as the fallback when `prepare_deployment` did not run |
| platform credentials | `artifacts/integration_test_setup.env` (dotenv: `CLIENT_SECRET`) |
| platform state | nothing but `needs:` order along `first_login` → `install_extensions` → `send_data` → `run_workflows` |
| "everything that used the VM is done" | `destroy_deployment`'s `needs:` list |

## Templates

| Template | Carries |
|---|---|
| `.test_template` | tests-stage runner tag, `python:3.12`, 5-minute timeout, pip cache, the `exec_unit_tests` rule |
| `.pytest_template` | plus the cobertura coverage report |
| `.build_cli_env` | build runner tag, `ci-base`, `environment: $REGISTRY_ENV`, full clone with tags, branch reconstruction |
| `.remote_execution_template` | deploy runner tag, `ci-base`, ansible env, SSH key permissions |
| `.integration_test_local` | the pytest invocation, `needs:` on the setup job, JUnit + log artifacts |

## Runners

Four Harvester VMs in namespace `kaapana-ci`, one runner registration each,
defined in [`ci/harvester/inventory.yaml`](../harvester/inventory.yaml). All use
the docker executor.

| VM | Tag | Size | limit | Special configuration |
|---|---|---|---|---|
| kaapana-tests-01 | `tests-runner` | 8 CPU / 16 Gi | 4 | privileged **services** matching `docker.io/library/docker:*` (dind for `task_api_tests`); `/builds` shared between job and services |
| kaapana-build-01 | `build-runner` | 32 CPU / 256 Gi / 512 Gi disk | 1 | host docker socket mounted into jobs → warm layer cache across pipelines |
| kaapana-security-01 | `security-runner` | 4 CPU / 8 Gi | 1 | small dedicated VM, so a long scan never blocks a build |
| kaapana-deploy-01 | `deploy-runner` | 8 CPU / 16 Gi | 4 | `/data` mounted for the test-data cache; no other machine state |

Provisioning and re-provisioning, which is also how you add a runner (extend the
inventory first):

```bash
export GITLAB_API_TOKEN=...      # api scope
export GITLAB_PROJECT_ID=...
export GITLAB_URL=https://codebase.helmholtz.cloud
export SSH_PUBLIC_KEY=~/.ssh/kaapana.pub
export SSH_PRIVATE_KEY=~/.ssh/kaapana.pem
export HARVESTER_KUBECONFIG=~/.kube/harvester.yaml

ansible-playbook -i ci/harvester/inventory.yaml ci/harvester/setup_ci.yaml
# FORCE_RECREATE=true deletes and recreates ALL existing VMs
```

On a runner VM the agent is a **user-mode** systemd service running as `ubuntu`:

```bash
gitlab-runner verify
systemctl --user status gitlab-runner
cat ~/.gitlab-runner/config.toml
```

## The ci-base image

One tool image for every job that needs more than plain Python:
[`ci/images/ci-base/Dockerfile`](../images/ci-base/Dockerfile). Contents: git,
docker CLI + buildx, helm (with the kubeval plugin, which `kaapana-build`
requires), trivy, dcmtk, nmap, jq, ansible, node 22 + npm, chromium for
playwright, snapd + squashfs-tools for the offline-package scan, and the pinned
Python test dependencies.

## Registries

Each registry has its own `CI_REGISTRY_URL` / `CI_REGISTRY_USER` /
`CI_REGISTRY_TOKEN` rows, stored under an environment *scope*
(`DKFZ_CONTAINER_REGISTRY`, `HIFIS_CONTAINER_REGISTRY`). Jobs declare
`environment: name: $REGISTRY_ENV`, so GitLab hands them the rows of that scope.

Switching registry is two steps:

1. Set `REGISTRY_ENV` to the scope name. Spell it exactly — a typo silently
   falls back to the `All (default)` rows.
2. Check that `DOCKER_AUTH_CONFIG` has an entry for the new host.

### `DOCKER_AUTH_CONFIG`

Runners pull the job image with this, before any job script runs:

```json
{"auths":{"registry-1":{"auth":"<base64 user:token>"},"registry-2":{"auth":"<base64 user:token>"}}}
```

Keep an entry for every registry in rotation, so switching never breaks image
pulls. Each token must be a deploy token with `read_registry` on the GitLab
instance that owns that registry.

| Symptom | Cause |
|---|---|
| Job dies in *prepare* with `failed to pull image … access forbidden`, and no `Authenticating with credentials from $DOCKER_AUTH_CONFIG` in the log | No entry for that host |
| `Login Succeeded`, then `denied` on push | docker ≥ 28 also reads `DOCKER_AUTH_CONFIG` from the job environment, where it overrides `docker login`. Pushing jobs must `unset DOCKER_AUTH_CONFIG` first |

## The DKFZ proxy

- For deployment on the targets behind the proxy, variables need to be set: `HTTP_PROXY, HTTPS_PROXY`

## Release pipelines

Pushing a protected tag `X.Y.Z` starts a normal pipeline with two differences,
both from `build_packages`'s tag rule: `rules:variables` swaps the registry
credentials to the protected `RELEASE_REGISTRY_*` triple, and the build is forced
cold (`docker system prune --all --volumes`). Images and charts land in the
release registry tagged `X.Y.Z`.

**Never create `REGISTRY_URL`, `REGISTRY_USER` or `REGISTRY_TOKEN` as project
variables.** A project variable outranks `rules:variables`, so their mere
existence sends a release build to the CI registry. That broke the 0.7.0 release.
The CI registry is configured under the `CI_REGISTRY_*` names instead.

## Workflow testcases (`ci-config`)

`run_workflows` collects every YAML document under any `<chart>/ci-config/*.yaml`
as one testcase: the document is the payload for
`kaapana-backend/client/workflow`, and the test passes when the triggered
workflow reaches a successful state. Three fields steer the CI and never reach
the platform:

| Field | Meaning |
|---|---|
| `ci_step: <name>` | the handle of this testcase, what a `ci_after` points at. Unique across all collected files, and only needed on a testcase something else depends on |
| `ci_after: [<name>, …]` | this testcase runs only after those testcases, on the same worker |
| `ci_ignore: true` | collect but do not run. Reported as passed, so it is not usable as a prerequisite |

**Everything is parallel by default.** A testcase without `ci_after` forms a group
of its own, so the workers distribute them freely. Documents of one file are *not*
a sequence: several documents usually mean parameter variants, and those must
stay independent.

**Declare a sequence only when a testcase needs state another one produces.**
Prerequisites, not positions:

```yaml
dag_id: "tag-dataset"
ci_step: evaluate-segmentations-tag-test
# ... tags one series with TEST
---
dag_id: "tag-dataset"
ci_step: evaluate-segmentations-tag-pred
# ... tags one series with PRED
---
dag_id: evaluate-segmentations
ci_step: evaluate-segmentations
ci_after:
  - evaluate-segmentations-tag-test
  - evaluate-segmentations-tag-pred
# ... selects its input by exactly those tags
```

Connected testcases become one xdist group, ordered so prerequisites run first.
The order follows the declarations, not the position in the file, so documents can
be reordered freely. The group is named after the alphabetically first `ci_step`
in it and appears in test ids as `test_workflow[dag]@group`.

**What is checked.** A name declared twice, a `ci_after` pointing at a name no
collected testcase declares, and a cycle all abort collection before any workflow
is triggered. At runtime each testcase verifies its prerequisites succeeded and
fails with `prerequisite '<name>' did not run on this worker` otherwise, so a
broken order is never silent.

**`PYTEST_DIST: "loadgroup"` is required** and set on the `run_workflows` job. The
xdist default `load` hands each test to the next free worker and ignores the
group, which would split a group and fail every testcase whose prerequisite ran
elsewhere; collection therefore aborts when a `ci_after` is declared without
`loadgroup`. `loadgroup` guarantees only that a group stays on one worker, not the
order within it — that is why the order comes from the declarations and is checked
at runtime. See the [xdist distribution
modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html). A run
without `-n` needs nothing: one process keeps every group together.

**Limits worth knowing.** A `ci_after` across files only resolves if both files are
collected in the same run, which matters when narrowing with `--files` or
`--test-dir`. And an order says nothing about state: if another testcase overwrites
the tags in between, the prerequisite is still green and the consumer still fails.
Prefer independent testcases over long chains.

Single testcase against a running platform:

```bash
pytest -s ci/ci-code/integration_tests/tests/test_run_workflows.py \
  --host <vm-fqdn> --client-secret <secret> \
  --files data-processing/kaapana-plugin/extension/kaapana-plugin-chart/ci-config/evaluate-segmentations.yaml
```

## Reports GitLab renders

Four report types are wired up. Only GitLab reads them; no job does.

| Report | Produced by | Where it shows |
|---|---|---|
| JUnit | every pytest job, `ui_e2e_tests`, `ui_unit_tests`, `playwright_ui_tests` | pipeline **Tests** tab, failed-test summary in the MR |
| Coverage (cobertura) | every job extending `.pytest_template` | coverage badge, line markers in the MR diff |
| Code Quality | `code_quality` | MR **Code Quality** widget |
| Container scanning | `security_scan` | MR security widget, vulnerability report |

Coverage is per suite — each job measures the one directory it exercises, and
GitLab merges the reports for the diff view.

## Adding a job

1. Extend the right template instead of repeating its settings.
2. Gate it with `rules:` on the matching `exec_*` input. The input must be declared
   in the stage file's own `spec:` block and passed down from the `include:` block
   in [`.gitlab-ci.yml`](../../.gitlab-ci.yml).
3. Needs a CI/CD variable that is not checked yet? Add it to `preflight_variables`.
4. Need docker? Prefer a plain daemonless service; a privileged dind service must
   use the fully-qualified image name (see `task_api_tests`).
5. **Add the job to `if_ci_failing`'s `needs:` list** (`optional: true`;
   `artifacts: true` only if its logs should feed the failure ticket — never for
   jobs whose artifacts contain secrets). If the job uses the test VM, **also add
   it to `destroy_deployment`'s `needs:` list**, the teardown barrier.
6. Talks to anything internal or job-local? Extend `NO_PROXY`/`no_proxy`, both
   casings. A nested `docker build` needs the proxy as a build arg.
7. New dependency between stages? Declare it in the header of the stage file that
   consumes it.

## Known gaps

- Between the integration test jobs, `needs:` order is the only guarantee.
  `first_login` → `install_extensions` → `send_data` → `run_workflows` pass
  platform state along.
- `install_extensions` and `send_data` carry `retry: 2` — known flakiness.
