# Kaapana CI

How to start a CI run, and everything you can change about one.

| Doc | Covers |
|---|---|
| this file | starting a run, inputs and variables, day-to-day configuration |
| [internals.md](internals.md) | how the pipeline is built: stages, jobs, handoffs, runners, images |
| [local-ci.md](local-ci.md) | running the jobs, or the deployment, on your own machine |

Configuration lives in [`.gitlab-ci.yml`](../.gitlab-ci.yml) plus one file per
stage under [`ci/pipeline/`](pipeline/).

## 1. How to run a pipeline

These start a pipeline without you asking:

| Trigger | What runs |
|---|---|
| Merge request | Full pipeline, all inputs at their defaults. A draft MR (Draft, WIP) runs nothing. Label the MR `Security` to add the security scan. |
| Push to `develop` | Full pipeline. Only happens after an MR. |
| Scheduled pipeline | Full pipeline plus whatever the schedule sets ([section 5](#scheduled-pipelines)). |
| Protected tag `X.Y.Z` | Release build, publishing to the release registry with a cold cache ([internals.md](internals.md#release-pipelines)). |

And these are the five ways to start one yourself.

### 1. Create a merge request

Push the branch, open the MR, and the full pipeline runs on every push to it.
This way the MR widgets are produced (test summary, coverage, security).

Mark the MR as draft to stop pipelines while you push work in progress.

### 2. From the merge request

The MR's **Pipelines** tab has a **Run pipeline** button. It re-runs the MR
pipeline on the current head — again with defaults.

To run an MR's branch *with modified values*, use a dropdown menu that leads you to a pre-configured run pipeline page. (see below)

### 3. From Build → Pipelines

**Build → Pipelines → Run pipeline**, pick the branch, and the form lists
every input with its description and default, plus a section for variables.
The descriptions are prefixed so the form reads grouped: `[exec]` (what runs),
`[runner]` (where it runs).

### 4. Using `glab ci run`

```bash
glab ci run -b my-branch \
  -i 'exec_unit_tests:bool(false)' \
  -i 'exec_integration_tests:bool(false)' \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.dkfz-heidelberg.de
```

| Flag | Passes |
|---|---|
| `-i key:value` | one input, repeatable |
| `--variables KEY:VALUE` | one variable, repeatable |
| `--variables-file KEY:path` | a File-type variable (an SSH key, a kubeconfig) |
| `-f, --variables-from file.json` | many variables, and the only way to pass a value containing a comma |
| `-b` | the branch or tag; defaults to the checked-out branch |
| `-w` | open the pipeline in a browser |

#### variables-from-file configuration

```json
[
  { "key": "DEPLOYMENT_INSTANCE_FQDN", "value": "e230-pc11.inet.dkfz-heidelberg.de", "variable_type": "env_var" },
  { "key": "DEPLOYMENT_INSTANCE_USER", "value": "ubuntu",      "variable_type": "env_var" }
]
```

#### Cheat sheet

```bash
glab ci run -b my-branch                            # full pipeline
glab ci run -b my-branch -i 'exec_build:bool(false)'  # one input, repeat -i for more
glab ci status -b my-branch --live                  # watch it
glab ci retry <JOB_ID>                              # one job, not the pipeline

P=projects/kaapana%2Fkaapana
glab api "$P/pipelines/<ID>/jobs?per_page=100"      # job ids, stages, statuses
glab api "$P/jobs/<ID>/trace"                       # full log
glab api "$P/jobs/<ID>/artifacts" > artifacts.zip
```

### 5. Using gitlab-ci-local

[gitlab-ci-local](https://github.com/firecow/gitlab-ci-local) runs the job
*scripts* in docker on your machine. 
- No pipeline or artifacts in GitLab
- No retry
- No runners involved.

```bash
npm install -g gitlab-ci-local

gitlab-ci-local --preview --variable CI_PIPELINE_SOURCE=web    # merged config
gitlab-ci-local --list    --variable CI_PIPELINE_SOURCE=web    # what would run
gitlab-ci-local unit_tests --variable CI_PIPELINE_SOURCE=web   # one job
```

#### Seeing the full configuration

The merged config — every `include:` resolved and `spec:inputs` substituted:

```bash
# from the working tree, with your input values
gitlab-ci-local --preview --variable CI_PIPELINE_SOURCE=web

# from the pushed ref, inputs at their defaults
glab api "projects/kaapana%2Fkaapana/ci/lint?ref=$(git branch --show-current)" \
  | jq -r .merged_yaml
```

In the UI it is **Build → Pipeline editor → Full configuration**, for the branch
selected in the editor. There is no per-pipeline view — a finished run does not
show the config it was created from.

- `glab ci lint` and `glab ci config compile` do **not** work here: they post
  your local file and resolve `local:` includes against the *default* branch, so
  a stage file whose `spec:` changed on your branch reads as broken
  (`Given inputs not defined in the spec section`).
- `dry_run=true` on that API call is unreliable too — it reports
  `preflight.yml`'s boolean inputs as missing on a config that creates pipelines
  fine.

## 2. What to run

**Inputs** decide which stages run and where. They are declared in the `spec:`
block at the top of [`.gitlab-ci.yml`](../.gitlab-ci.yml) and each included YAML file. 

| Input | Default | Meaning |
|---|---|---|
| `exec_unit_tests` | `true` | tests stage: unit tests + documentation build |
| `exec_lint` | `true` | tests stage: ruff check + code quality report |
| `exec_build` | `true` | build stage: full platform build |
| `exec_build_arguments` | `""` | extra `kaapana-build` flags, e.g. `--build-only`, `--cache-from` |
| `exec_deploy` | `true` | deploy stage: target/VM + platform installation |
| `exec_server_installation` | `true` | `true` installs microk8s and helm on the target (needs passwordless sudo). `false` assumes a prepared target and checks it read-only |
| `exec_redeploy` | `false` | `false` makes an already-deployed platform a fatal check; `true` undeploys it first |
| `exec_integration_tests` | `true` | test stage: pytest + Playwright against the deployed platform |
| `exec_security_scan` | `false` | trivy scan of the images this commit resolves to |
| `exec_security_scan_arguments` | `--vulnerability-scan --configuration-check` | flags for that scan |
| `exec_docker_prune` | `false` | wipe the build runner's docker cache first (cold build) |
| `exec_destroy_delayed` | `false` | keep the test VM for 4 h after the pipeline |
| `tests_runner_tag` | `tests-runner` | runner for preflight and the tests stage |
| `build_runner_tag` | `build-runner` | runner for the CI image and build stages |
| `security_runner_tag` | `security-runner` | runner for the security stage |
| `deploy_runner_tag` | `deploy-runner` | runner for deploy, integration tests and clean |

**Variables** carry everything else: the deployment target, secrets, network
settings, and the two remaining `CI_EXEC_*` switches.

| Variable | Meaning |
|---|---|
| `DEPLOYMENT_INSTANCE_FQDN` | Deployment target. Empty provisions a fresh Harvester VM; set deploys onto that host and never destroys it. Max 57 characters (`dcmsend` peerhost limit) and it must resolve *inside the job container* |
| `DEPLOYMENT_INSTANCE_USER` | SSH user on the target, default `ubuntu` |
| `DEPLOYMENT_INSTANCE_CPU` / `_MEMORY` / `_DISK` / `_IMAGE_ID` / `_NETWORK` / `_STORAGE_CLASS` | shape of the provisioned VM |
| `CI_EXEC_SECURITY_SCAN` | `"true"` runs the security stage. Also what the `Security` MR label sets |
| `CI_EXEC_INTEGRATION_TEST_JOBS` | comma-separated allowlist of integration-test jobs (`scan_ports`, `first_login`, `install_extensions`, `send_data`, `run_workflows`). Unset runs all of them; `playwright_ui_tests` ignores the list |
| `NO_PROXY` / `no_proxy` | proxy exemptions, always in both casings |
| `MAINTENANCE` | `"true"` pauses MR, push and schedule pipelines |
| `ANSIBLE_VERBOSITY` | `1`–`4` for a talkative deploy job |
| `ANSIBLE_SSH_COMMON_ARGS` | no job sets it, so it reaches every deploy job — this is where a `ProxyCommand` goes |

### CI_EXEC variables vs inputs

The stage toggles used to be `CI_EXEC_*` variables. They are inputs now, and
the old names are inert — a run with `--variables CI_EXEC_BUILD:false` builds
anyway, silently. Translate:

| Old variable | Now |
|---|---|
| `CI_EXEC_UNIT_TESTS` | `-i 'exec_unit_tests:bool(false)'` |
| `CI_EXEC_LINT` | `-i 'exec_lint:bool(false)'` |
| `CI_EXEC_BUILD` | `-i 'exec_build:bool(false)'` |
| `CI_EXEC_BUILD_ARGUMENTS` | `-i 'exec_build_arguments:--build-only'` |
| `CI_EXEC_DEPLOY` | `-i 'exec_deploy:bool(false)'` |
| `CI_EXEC_SERVER_INSTALLATION` | `-i 'exec_server_installation:bool(false)'` |
| `CI_EXEC_INTEGRATION_TESTS` | `-i 'exec_integration_tests:bool(false)'` |
| `CI_EXEC_SECURITY_SCAN_ARGUMENTS` | `-i 'exec_security_scan_arguments:…'` |
| `CI_EXEC_DOCKER_PRUNE` | `-i 'exec_docker_prune:bool(true)'` |
| `CI_EXEC_DESTROY_DELAYED` | `-i 'exec_destroy_delayed:bool(true)'` |
| `CI_EXEC_SECURITY_SCAN` | still a variable |
| `CI_EXEC_INTEGRATION_TEST_JOBS` | still a variable |

`CI_EXEC_REDEPLOY` is internal: the deploy jobs set it from
`exec_redeploy` because the ansible playbooks read it from the environment.

Two consequences worth remembering:

- Anything that can only post variables — a webhook, a trigger token, an old
  bookmarked API call — cannot pick stages any more.
- A scheduled pipeline has to set *inputs*, not `CI_EXEC_*` variables
  ([section 5](#scheduled-pipelines)).

## 3. Recipes

**Unit tests only**

```bash
glab ci run -b my-branch -i 'exec_build:bool(false)' \
  -i 'exec_deploy:bool(false)' -i 'exec_integration_tests:bool(false)'
```

**Build only**

```bash
glab ci run -b my-branch -i 'exec_unit_tests:bool(false)' \
  -i 'exec_deploy:bool(false)' -i 'exec_integration_tests:bool(false)'
```

**Deploy without rebuilding** — only if this commit was already built and
pushed; `prepare_deployment` fails fast otherwise, before any VM exists.

```bash
glab ci run -b my-branch -i 'exec_unit_tests:bool(false)' -i 'exec_build:bool(false)'
```

**Deploy onto a host you own** — full walkthrough, including the readiness
check to run first, in [local-ci.md](local-ci.md#scenario-2-deploy-the-platform-on-your-machine).

```bash
glab ci run -b my-branch \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER \
  -i 'exec_server_installation:bool(false)'
```

**Move a stage to another runner** — the tag has to exist on a runner
registered to this project. Registering your own is
[local-ci.md scenario 1](local-ci.md#scenario-1-run-the-jobs-on-your-machine).

```bash
glab ci run -b my-branch -i tests_runner_tag:my-tag \
  -i build_runner_tag:my-tag -i deploy_runner_tag:my-tag
```

**One integration test job**

```bash
glab ci run -b my-branch --variables CI_EXEC_INTEGRATION_TEST_JOBS:send_data
```

**Keep the test VM to debug a failure** — it survives 4 h; cancel the delayed
`destroy_deployment` for longer, or start it manually when you are done.

```bash
glab ci run -b my-branch -i 'exec_destroy_delayed:bool(true)'
```

**SSH into the test VM** — the FQDN is in the `prepare_deployment` log and in
its `deployment.env` artifact; the key is the `DEPLOYMENT_INSTANCE_SSH_KEY`
File variable (the Harvester `kaapana` KeyPair). The platform UI is at
`https://<vm-fqdn>`, and `platform_deployment`'s log ends with the Keycloak
admin password.

```bash
ssh -i <kaapana-key> ubuntu@<vm-fqdn>
```

**Security scan on demand** — `-i 'exec_security_scan:bool(true)'`, or label
the MR `Security`. It does not need a build in the same pipeline: with
`exec_build:false` it scans whatever tag this commit already resolves to in
the registry. A failed scan still publishes what it managed to check.

```bash
glab ci run -b my-branch -i 'exec_security_scan:bool(true)' \
  -i 'exec_security_scan_arguments:--vulnerability-scan --create-sboms'
```

The same scan runs locally — it is `kaapana-build`, not a pipeline-only tool:

```bash
export REGISTRY_URL=<your-registry> REGISTRY_PW=<token>
kaapana-build --scan-only --vulnerability-scan --offline-packages-scan \
  --default-registry "$REGISTRY_URL" --kaapana-dir .
```

Reports land in `reports/`; which file appears depends on the flags
([internals.md](internals.md#security)).

**Delete a leftover test VM** (normally never needed)

```bash
export HARVESTER_KUBECONFIG=~/.kube/harvester.yaml
kubectl --kubeconfig $HARVESTER_KUBECONFIG -n kaapana-ci get vm   # ci-<branch>-<sha>
ansible-playbook -i localhost, ci/ci-code/deploy/delete_harvester_vm.yaml \
  -e vm_name=<name>
```

**Pause all CI** — set the project variable `MAINTENANCE=true`; remove it to
resume. Web and API runs still start.

**Retrying a deploy job does not re-trigger teardown.** GitLab never cascades
retries, so a `destroy_deployment` that already ran stays in its old state. If
a retried `prepare_deployment` provisioned a VM, retry `destroy_deployment`
afterwards (↻ on the job) or the VM leaks.

## 4. When a job is red

Every job uploads its logs and reports as artifacts (job page → Browse) — look
there before re-running. Grep a trace for the *first* error, not the last line;
the tail is usually artifact-upload noise. Failures on `develop` open a GitLab
issue with the collected logs and post to Slack (`if_ci_failing`).

| Symptom | Likely cause / what to do |
|---|---|
| A stage runs although you switched it off | You set a `CI_EXEC_*` variable. The toggles are inputs ([section 2](#2-what-to-run)) |
| Job stuck "pending" | No runner with the required tag is picking it up ([internals.md](internals.md#runners)) |
| Job dies in *prepare*: `failed to pull image … ci-base … access forbidden` | `DOCKER_AUTH_CONFIG` has no entry for the active registry host, or its token was minted on the wrong GitLab instance ([section 5](#docker_auth_config)) |
| Everything fails weirdly right after a CI-image change | `CI_IMAGES_TAG` was not bumped ([section 5](#the-ci-image-tag)) |
| Unit-test job fails in `pip install` | Dependency change in that component. Reproduce locally — the job runs plain `python:3.12` |
| `task_api_tests` cannot reach `docker:2375` (`connection refused`, `No route to host`) | Its dind service died — read the **Service container logs** block near the top of the job log, not the pytest traceback |
| A job times out talking to a service (e.g. `registry:5000`) | DKFZ proxy. The alias must be in `NO_PROXY` **and** `no_proxy` |
| A tool inside a job has no internet, but `pip`/`npm` do | `apt` reads only the lowercase `http_proxy`/`https_proxy`. A job that overrides the proxy must set both casings |
| A `docker build` inside a job has no internet | Build containers do not inherit the job environment. Pass the proxy as `--build-arg` |
| A job hits the 5-minute `.test_template` cap | Either the suite got slower or the runner is slower than the cap assumes. Split the suite, or raise `timeout:` on the job |
| `build_packages` fails immediately | Registry login (`CI_REGISTRY_*`) or the build VM's docker daemon. Full log in the `build.log` artifact |
| `build_packages` fails on one image | Search the trace for `container build failed` — that line names the image and carries the docker output. Usually reproducible with `kaapana-build` locally |
| Build very slow | Cold layer cache — `exec_docker_prune`, a release tag, or a new build VM |
| `prepare_deployment` fails provisioning | Harvester capacity or API; `HARVESTER_KUBECONFIG`'s identity may lack a permission (`… is forbidden: User "…" cannot …`) |
| `prepare_deployment`: `chart … not found in registry` | The commit was never built. Build it first |
| `preflight_target`: platform already on the target | Undeploy it there, or re-run with `exec_redeploy:bool(true)` |
| Integration test failed, VM already gone | Re-run with `exec_destroy_delayed:bool(true)`, then SSH in |
| `install_extensions` / `send_data` flaky | Known flakiness, `retry: 2` masks most of it. Three failures in a row is real; check the JUnit and log artifacts |
| `send_data`: `… unavailable from all source(s)` | Every test-data source failed for that series; the log lists each error |
| `playwright_ui_tests` fails | Download the Playwright HTML report artifact — it has traces and screenshots |
| `run_workflows` fails | The trace embeds the Airflow task logs of the failed DAG run. Note the job is `allow_failure: true`, so it reddens the job, not the pipeline |

## 5. Configuration

### Project CI/CD variables

Only secrets and registry configuration live as project variables
(Settings → CI/CD → Variables); everything else defaults in
[`.gitlab-ci.yml`](../.gitlab-ci.yml). Do not mirror config values into project
variables — a project variable outranks `rules:variables`, which is exactly how
the 0.7.0 release broke.

| Variable | Type | Description |
|---|---|---|
| `CI_REGISTRY_URL` | | Registry for CI builds |
| `CI_REGISTRY_USER` | | Username for `CI_REGISTRY_TOKEN`. Shadows a GitLab-predefined variable: if the project variable is deleted, jobs silently get `gitlab-ci-token` and `preflight_variables` fails on that value |
| `CI_REGISTRY_TOKEN` | masked | Registry push credential; also the default for `GITLAB_API_TOKEN` and `BLABLADOR_API_TOKEN` |
| `REGISTRY_ENV` | | Which registry scope build and deploy use (below) |
| `RELEASE_REGISTRY_URL` / `_USER` / `_TOKEN` | protected | Release registry, used only by release tag pipelines |
| `DOCKER_IO_USER` / `DOCKER_IO_PASSWORD` | masked password | docker.io account, to dodge anonymous pull rate limits. Leave both empty to skip that login |
| `DOCKER_AUTH_CONFIG` | | Pull auth for the `ci-base` job image (below) |
| `HARVESTER_KUBECONFIG` | File | Harvester access for VM provisioning and deletion (`kaapana-ci` ServiceAccount) |
| `DEPLOYMENT_INSTANCE_SSH_KEY` | File | SSH key for the deployment target (Harvester `kaapana` KeyPair) |
| `CI_TEST_DATA_REPOS` | File | Test-data repositories for `send_data` |
| `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID` | masked | Failure notifications on `develop` |
| `KAAPANA_READTHEDOCS_TOKEN` | masked | Scheduled docs build check |

`preflight_variables` ([`ci/pipeline/preflight.yml`](pipeline/preflight.yml))
checks at the start of every pipeline that the variables the *enabled* stages
need are usable, and fails in seconds naming the missing one. A new required
variable belongs in that job too.

Bulk upload from a template:

```bash
cp ci/harvester/control/ci_variables_template.json /tmp/ci_variables.json  # fill in
python3 ci/harvester/control/set_ci_variables.py \
  --ci-vars-file /tmp/ci_variables.json --dry-run   # drop --dry-run to upload
```

The script cannot set protected variables — create the `RELEASE_REGISTRY_*`
triple by hand.

### Selecting the registry

The CI can build and push to any configured registry. Each one gets its own
`CI_REGISTRY_URL` / `CI_REGISTRY_USER` / `CI_REGISTRY_TOKEN` rows, stored under
an environment *scope* (`DKFZ_CONTAINER_REGISTRY`, `HIFIS_CONTAINER_REGISTRY`).
Jobs that need the registry declare `environment: name: $REGISTRY_ENV`, so
GitLab hands them the rows of whichever scope `REGISTRY_ENV` names.

Switching registry is therefore one variable: set the `REGISTRY_ENV` project
variable to that scope. Two things to keep in mind — the scope string has to
match the variable rows exactly, or the jobs silently fall back to the
`All (default)` rows, and `DOCKER_AUTH_CONFIG` needs an entry for the new host.

### `DOCKER_AUTH_CONFIG`

Runners pull the `ci-base` job image with this, before any job script runs:

```json
{"auths":{"registry-1":{"auth":"<base64 user:token>"},"registry-2":{"auth":"<base64 user:token>"}}}
```

- Keep an entry for every registry in rotation, then switching registry never
  breaks image pulls. Adding a registry means adding its entry in the same change.
- Each token must be a deploy token with `read_registry` on the GitLab instance
  that owns that registry.
- Missing or mismatched entry: the job dies in *prepare* with `failed to pull
  image … access forbidden`, and the log does **not** say `Authenticating with
  credentials from $DOCKER_AUTH_CONFIG`.
- docker ≥ 28 reads `DOCKER_AUTH_CONFIG` from the job environment too, where it
  overrides `docker login`. Jobs that push images `unset DOCKER_AUTH_CONFIG`
  first. Symptom of forgetting: `Login Succeeded` followed by `denied` on push.

### The CI image tag

One image, `ci-base`, for every job that needs CI tooling
([internals.md](internals.md#the-ci-base-image)). **Change the image → bump
`CI_IMAGES_TAG` in the same MR.** Runners pull `if-not-present`, so re-pushing
an existing tag leaves warm runners on the stale image, silently.

### Scheduled pipelines

Build → Pipeline schedules. Two are active, and the GitLab host allows at most
three.

| Schedule | Ref | Time | Purpose |
|---|---|---|---|
| `develop` | `develop` | 00:00 Europe/Berlin | nightly full run, refresh the registry cache, vulnerability report |
| `Build latest release` | latest release tag | 21:00 Europe/Berlin | prove the release still builds from scratch |

A schedule sets **inputs** in its own form; its variables can no longer pick
stages ([section 2](#ci_exec-variables-vs-inputs)). What each schedule wants:

| Schedule | Inputs |
|---|---|
| nightly `develop` | `exec_security_scan:true`, `exec_build_arguments:--cache-to --cache-from -pp 8` |
| release rebuild | `exec_docker_prune:true`, `exec_build_arguments:--build-only` |

The `develop` nightly is also the only pipeline that runs `check_readthedocs`.

### Runner tags

Four Harvester VMs, one runner each: `tests-runner`, `build-runner`,
`security-runner`, `deploy-runner`. Sizes, special configuration and
re-provisioning are in [internals.md](internals.md#runners); pointing a stage
at your own machine is [local-ci.md](local-ci.md#scenario-1-run-the-jobs-on-your-machine).

## 6. Linting

Ruff, the pre-commit hook and the local commands are in the development guide:
[Code Formatting](../docs/source/development_guide/legacy/code_formatting.rst).
The CI-specific parts:

| Config | Ruleset | Used by |
|---|---|---|
| [`ruff.toml`](../ruff.toml) | enforced: `E4`, `E7`, `E9`, `F`, `I`, 120 columns | pre-commit, and the `lint` job |
| [`ci/ruff-quality.toml`](ruff-quality.toml) | advisory: adds `B`, `C4`, `SIM`, `UP`, `RUF`, `W` | the `code_quality` job only |

Both jobs are in [`ci/pipeline/lint.yml`](pipeline/lint.yml) and neither blocks
a merge: `lint` is `allow_failure: true`, `code_quality` always exits zero and
only publishes the report.
