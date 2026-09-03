# Kaapana CI

How to run, debug, and extend the Kaapana CI pipeline.

Configuration lives in [`.gitlab-ci.yml`](../.gitlab-ci.yml) plus one file per
stage under [`ci/pipeline/`](pipeline/). Each stage file's header states what
the stage takes in and hands out — an MR that adds an undeclared dependency
must extend that header.

Running the pipeline on your own machine, or deploying onto it, is
[ci/local-ci.md](local-ci.md).

## Cheat sheet

```bash
glab ci run -b my-branch                      # full pipeline
glab ci run -b my-branch -i exec_build:false  # one input, repeat -i for more
glab ci status -b my-branch --live            # watch it
glab ci retry <JOB_ID>                        # one job, not the pipeline

P=projects/kaapana%2Fkaapana
glab api "$P/pipelines/<ID>/jobs?per_page=100"   # job ids, stages, statuses
glab api "$P/jobs/<ID>/trace"                    # full log
glab api "$P/jobs/<ID>/artifacts" > artifacts.zip
```

Inputs are also the **Run pipeline** form in the UI. A CI/CD variable named
after an input has no effect.

## 1. What the pipeline does

Test the code → build the platform images → deploy them on a fresh throwaway
VM → test that live deployment → delete the VM.

| Stage | Jobs | Runs on |
|---|---|---|
| `preflight` | `preflight_variables`; `preflight_target` when a target is given by FQDN | tests runner |
| `tests` | unit-test suites, `ui_e2e_tests` (one job per frontend app), docs build | tests runner |
| `build` | `build_packages`, `security_scan` | build runner |
| `deploy` | `prepare_deployment` → `server_installation` or `target_readiness` → `platform_deployment` | deploy runner (Ansible over SSH) |
| `test` | integration tests: login, ports, UI, extensions, DICOM data, workflows | deploy runner, against the live VM |
| `clean` | `destroy_deployment`, `if_ci_failing` | deploy runner |

Three facts explain most of the design:

- **Every job runs in a fresh container.** Nothing persists on the machines;
  credentials come from File-type CI variables.
- **The registry is the only handoff between build and deploy.** Both derive
  the same tag from `git describe`; `prepare_deployment` verifies the chart
  exists before any VM is created, and hands the tag to later jobs via the
  `deployment.env` dotenv artifact.
- **The test VM is disposable.** `destroy_deployment` deletes it even on
  failure — except a target given by FQDN, which is never destroyed, or when
  you asked to keep it.

## 2. What runs when

| Trigger | What runs |
|---|---|
| Merge request | Full pipeline. `Draft:` MRs run nothing. |
| Push to `develop` | Full pipeline. |
| Nightly schedule | Full pipeline + security scan + ReadTheDocs check. |
| Release tag `X.Y.Z` | Full pipeline, publishing to the release registry with a cold cache ([section 7](#7-releases)). |
| Web UI / API / trigger | Always allowed; you pick the inputs. |

`MAINTENANCE=true` (project variable) pauses MR, push and schedule pipelines;
web and API runs still start. `ci/utils/trigger_pipeline.py` posts variables
only, so it cannot set inputs.

### Inputs

The `spec:` block at the top of [`.gitlab-ci.yml`](../.gitlab-ci.yml) is
authoritative — it carries every input's type, default and description. The
descriptions are prefixed so the form reads grouped:

| Prefix | Covers |
|---|---|
| `[exec]` | which stages run, and their arguments |
| `[runner]` | which runner tag each stage group lands on |
| `[target]` | where the platform gets deployed |

Two that need more than one line:

- **`exec_server_installation`** picks which readiness path runs.
  `true` → `server_installation` installs microk8s and helm on the target
  (needs passwordless sudo there). `false` → the target is assumed prepared,
  and it is checked read-only by `preflight_target` (target given by FQDN) or
  `target_readiness` (provisioned VM).
- **`deployment_fqdn`** empty provisions a fresh Harvester VM; set deploys onto
  that host instead. Max 57 characters — the `dcmsend` peerhost limit, enforced
  by a `regex` on the input.

Boolean inputs accept both `-i exec_build:false` and the explicit
`-i 'exec_build:bool(false)'`.

## 3. Recipes

**Unit tests only**

```bash
glab ci run -b my-branch -i exec_build:false -i exec_deploy:false \
  -i exec_integration_tests:false
```

**Build only**

```bash
glab ci run -b my-branch -i exec_unit_tests:false -i exec_deploy:false \
  -i exec_integration_tests:false
```

**Deploy without rebuilding** — only if this commit was already built and
pushed; `prepare_deployment` fails fast otherwise.

```bash
glab ci run -b my-branch -i exec_unit_tests:false -i exec_build:false
```

**Deploy onto a host you own** — full walkthrough in
[ci/local-ci.md](local-ci.md).

```bash
glab ci run -b my-branch \
  -i deployment_fqdn:my-host.dkfz-heidelberg.de -i deployment_user:my-user
```

**Move a stage to another runner** — the tag has to exist on a runner
registered to this project.

```bash
glab ci run -b my-branch -i tests_runner_tag:my-tag -i build_runner_tag:my-tag \
  -i deploy_runner_tag:my-tag
```

**Keep the test VM to debug a failure** — the VM survives 4 h; cancel the
delayed `destroy_deployment` for longer, or start it manually when done.

```bash
glab ci run -b my-branch -i exec_destroy_delayed:true
```

**SSH into the test VM** — FQDN is in the `prepare_deployment` log and its
`deployment.env` artifact; the key is the `CI_SSH_PRIVATE_KEY` File variable
(the Harvester `kaapana` KeyPair). The platform UI is at `https://<vm-fqdn>`.

```bash
ssh -i <kaapana-key> ubuntu@<vm-fqdn>
```

**Security scan on demand** — needs the build stage. Reports: `security_scan`
artifacts (JSON per image), `vulnerability_report.html`, GitLab's Security tab.

```bash
glab ci run -b my-branch -i exec_security_scan:true
```

**Delete a leftover test VM** (normally never needed)

```bash
export HARVESTER_KUBECONFIG=~/.kube/harvester.yaml
kubectl --kubeconfig $HARVESTER_KUBECONFIG -n kaapana-ci get vm   # ci-<branch>-<sha>
ansible-playbook -i localhost, ci/ci-code/deploy/delete_harvester_vm.yaml \
  -e vm_name=<name>
```

**Pause the CI** — set project variable `MAINTENANCE=true`
(Settings → CI/CD → Variables); remove it to resume.

**Retrying a deploy job does not re-trigger teardown.** GitLab never cascades
retries, so a `destroy_deployment` that already ran stays in its old state. If
a retried `prepare_deployment` provisioned a VM, retry `destroy_deployment`
afterwards (↻ on the job) or the VM leaks.

## 4. When a job is red

Every job uploads its logs and reports as artifacts (job page → Browse) — look
there before re-running. Grep a trace for the *first* error, not the last line;
the tail is usually artifact-upload noise. Failures on `develop` open a GitLab
issue with collected logs and post to Slack (`if_ci_failing`).

| Symptom | Likely cause / what to do |
|---|---|
| Unit-test job fails in `pip install` | Dependency change in the component. Reproduce locally — the job runs plain `python:3.12`. |
| `task_api_tests` cannot reach `docker:2375` ("connection refused", `[Errno 113] No route to host`) | Its dind service died — read the **Service container logs** block near the top of the job log, not the pytest traceback. Causes in [section 6](#6-runners). |
| Test job times out talking to a service (e.g. `registry:5000`) | DKFZ proxy. The alias must be in `NO_PROXY` **and** `no_proxy` (both casings) in the job variables. |
| A tool inside a job cannot reach the internet, but `pip`/`npm` can | `apt` reads only the lowercase `http_proxy`/`https_proxy`. Both casings are set globally; a job that overrides them must set both. |
| A `docker build` inside a job cannot reach the internet | Build containers do not inherit the job environment. Pass the proxy as `--build-arg` / `buildargs`. |
| `build_packages` fails immediately | Registry login (`CI_REGISTRY_*`) or the build VM's docker daemon. Full log in the `build.log` artifact. |
| `build_packages` fails on one image | Search the trace for `container build failed` — that line names the image and carries the docker output. Usually reproducible locally with `kaapana-build`. |
| Build very slow | Cold layer cache (`exec_docker_prune`? new build VM?). |
| `prepare_deployment` fails provisioning | Harvester capacity or API — check the job log. |
| `prepare_deployment`: "chart … not found in registry" | The commit was never built. Build it first. |
| `preflight_target`: platform already on the target | Undeploy it there, or re-run with `exec_redeploy:true`. |
| Integration test failed, VM already gone | Re-run with `exec_destroy_delayed:true`, then SSH in. |
| `install_extensions` / `send_data` flaky | Known flakiness, `retry: 2` masks most of it. Fails 3× → real; check the JUnit/log artifacts. |
| `playwright_ui_tests` fails | Download the Playwright HTML report artifact — traces and screenshots. |
| `run_workflows` fails | The trace embeds the Airflow task logs of the failed DAG run. |
| Job dies in *prepare*: `failed to pull image … ci-base … access forbidden` | `DOCKER_AUTH_CONFIG` missing an entry for the active registry host, or its token was minted on the wrong GitLab instance ([section 8](#8-project-cicd-variables-secrets)). |
| A stage runs although you switched it off | You set a `CI_EXEC_*` variable. The toggles are inputs: `-i exec_*:false` ([section 2](#2-what-runs-when)). |
| `prepare_deployment`: `… is forbidden: User "…" cannot …` | `HARVESTER_KUBECONFIG`'s identity lacks that permission ([section 6](#6-runners)). |
| Job stuck "pending" | No runner with the required tag is picking it up ([section 6](#6-runners)). |
| A job times out at the `.test_template` cap | Either the suite got slower, or the runner is slower than the cap assumes. Split the suite, or raise `timeout:` on the job. |
| Everything fails weirdly after a CI-image change | Tag wasn't bumped — bump `CI_IMAGES_TAG` and re-run ([section 5](#5-the-ci-image-ci-base)). |

## 5. The CI image (`ci-base`)

One tool image for all jobs that need CI tooling:
[`ci/images/ci-base/Dockerfile`](images/ci-base/Dockerfile), build context
`ci/`, not the repo root. Lives at `$CI_REGISTRY_URL/ci-base:$CI_IMAGES_TAG`
and is rebuilt by `build_ci_image` when its inputs change.

**The one rule: change the image → bump `CI_IMAGES_TAG` in the same MR.**
Runners pull with `if-not-present`, so re-pushing an existing tag leaves warm
runners on the stale image, silently. With a bump, `build_ci_image` pushes the
new tag before the later stages pull it.

Bootstrap by hand (empty registry, broken automation):

```bash
docker login $CI_REGISTRY_URL
docker build --build-arg http_proxy="$HTTP_PROXY" --build-arg https_proxy="$HTTPS_PROXY" \
  -f ci/images/ci-base/Dockerfile -t $CI_REGISTRY_URL/ci-base:<tag> ci
docker push $CI_REGISTRY_URL/ci-base:<tag>
```

## 6. Runners

Runner VMs live on Harvester in namespace `kaapana-ci` and are defined in
[`ci/harvester/inventory.yaml`](harvester/inventory.yaml) — that file is the
authoritative list. All use the docker executor. Roles by tag:

| Tag | Special configuration |
|---|---|
| `tests-runner` | Allows privileged **services** matching `docker.io/library/docker:*` (dind for `task_api_tests`); `/builds` shared between job and services |
| `build-runner` | Host docker socket mounted into jobs → warm layer cache across pipelines |
| `deploy-runner` | No machine state; credentials from File-type CI variables |
| `security-runner` | Registry scanning only |

Provision or re-provision — also how you add a runner, after adding it to the
inventory:

```bash
export GITLAB_API_TOKEN=...      # api scope
export GITLAB_PROJECT_ID=...
export GITLAB_URL=https://codebase.helmholtz.cloud
export SSH_PUBLIC_KEY=~/.ssh/kaapana.pub
export SSH_PRIVATE_KEY=~/.ssh/kaapana.pem
export HARVESTER_KUBECONFIG=~/.kube/harvester.yaml

ansible-playbook -i ci/harvester/inventory.yaml ci/harvester/setup_ci.yaml
# FORCE_RECREATE=true → delete and recreate existing VMs
```

The runner agent is a `gitlab/gitlab-runner` container, not an apt package
under systemd. It mounts the host docker socket and creates job containers as
siblings on the host daemon, so bind mounts in `config.toml` resolve against
host paths. The playbook removes a host-installed runner first, so
re-provisioning an older VM converts it.

On-VM troubleshooting, all as `ubuntu` with no sudo:

```bash
docker exec gitlab-runner gitlab-runner verify
docker logs gitlab-runner
docker restart gitlab-runner
grep -vE '^  token' ~/.gitlab-runner/config.toml   # bind-mounted into the container
```

From anywhere — which runners this project can actually use:

```bash
glab api "projects/kaapana%2Fkaapana/runners?per_page=50"   # id, description, status
glab api "/runners/<ID>"                                    # tag_list, paused, projects
```

A runner that answers `verify` but never picks up a job is usually registered
to a different project, paused, or carrying a tag no input points at — that API
call shows all three.

### The two docker modes

| | Host socket (`build-runner`) | dind service (`tests-runner`) |
|---|---|---|
| How | bind-mounted `/var/run/docker.sock` | privileged dind sidecar (`dind_image` input) at `tcp://docker:2375` |
| Layer cache | survives across pipelines | empty every run |
| Isolation | all jobs share the host daemon; a job holds root on the host | clean per job, nothing leaks to the host |
| Gotchas | `docker system prune` is host-wide; `-v` paths resolve on the host, not in the job container | image name must stay fully qualified (the allowlist matches the literal string); `DOCKER_TLS_CERTDIR: ""`; every mounted path under `$CI_PROJECT_DIR` |

**The two cannot be combined on one runner.** `volumes` under
`[runners.docker]` applies to service containers as well as the job container,
and there is no service-only volume setting. A mounted host socket therefore
lands on `/var/run/docker.sock` inside the dind service, exactly where its own
dockerd wants to create one:

```
failed to load listeners: can't create unix socket /var/run/docker.sock: device or resource busy
```

Nothing then listens on `docker:2375`. Keep the roles split when adding a
runner to the inventory.

One machine that must do both can, by mounting the socket somewhere else and
pointing build jobs at it:

```toml
volumes     = ["/cache", "/builds", "/var/run/docker.sock:/var/run/host-docker.sock"]
environment = ["DOCKER_HOST=unix:///var/run/host-docker.sock"]
```

That is how a workstation runner takes all three stages — see
[ci/local-ci.md](local-ci.md).

### Runner performance

A runner slower than the one a job was calibrated on shows up as timeouts and
flaky service connections, not as an obvious "slow" signal. Two measurements
separate a slow CPU from slow storage:

```bash
# synchronous write latency — what pip, npm, apt and registry pushes wait on
dd if=/dev/zero of=/tmp/io.bin bs=4k count=500 oflag=dsync; rm -f /tmp/io.bin

# single-thread speed — what chromium and vite wait on
python3 -c 'import time;t=time.perf_counter();x=0
for i in range(6_000_000): x=(x*31+i)&0xFFFFFFFF
print(f"{time.perf_counter()-t:.2f}s")'
```

Buffered throughput (`conv=fdatasync` on a large file) is not the number that
matters: `fsync` bypasses the page cache, so RAM does not help it. Install-heavy
jobs suffer most from sync latency, browser jobs from single-thread speed.

Levers, cheapest first: `pull_policy = "if-not-present"` in `config.toml`;
`/builds` on tmpfs where the host has spare RAM; a per-job service kept off disk
(`REGISTRY_STORAGE: "inmemory"` for a registry service); raising `timeout:` on
jobs whose cap was set for faster hardware.

### Harvester access (`HARVESTER_KUBECONFIG`)

The deploy stage needs one credential: a kubeconfig whose identity may make
these calls in `DEPLOYMENT_INSTANCE_HARVESTER_NAMESPACE` (`kaapana-ci`).
Nothing else, and nothing cluster-scoped.

| Resource | Verbs | Used for |
|---|---|---|
| `kubevirt.io` virtualmachines | get, list, watch, create, delete | the test VM, and waiting for it |
| `harvesterhci.io` virtualmachineimages, keypairs | get, list | resolve the boot image by display name, read the SSH public key |
| secrets | get, list, create, patch, delete | the per-VM `<vm>-cloudinit` Secret |
| persistentvolumeclaims | get, list, watch, patch, delete | the root disk: wait for it, own it, delete it |
| `k8s.cni.cncf.io` network-attachment-definitions | get, list | only if `DEPLOYMENT_INSTANCE_NETWORK` names another namespace, as `harvester-public/dkfz-net` does |

With cluster-admin rights on the target cluster, any kubeconfig covering that
table works — export it, upload it, done.

Without them, make a ServiceAccount in that namespace, have whoever administers
the cluster grant it the table above, and build a kubeconfig from its token —
[the method](https://ryanbaker.io/2021-07-26-svc-acct-kubectl/). The DKFZ side
of that, who to ask and what to send them, is in the Handbook.

```bash
NS=kaapana-ci
SERVER=<harvester-api-server-url>
KUBECTL="kubectl --kubeconfig $HOME/.kube/harvester.yaml -n $NS"

$KUBECTL get secret kaapana-ci-token -o jsonpath='{.data.token}' | base64 -d > /tmp/sa.token
$KUBECTL get secret kaapana-ci-token -o jsonpath='{.data.ca\.crt}' | base64 -d > /tmp/harvester-ca.crt

export KUBECONFIG=/tmp/harvester-ci.kubeconfig
kubectl config set-cluster harvester --server=$SERVER \
  --certificate-authority=/tmp/harvester-ca.crt --embed-certs=true
kubectl config set-credentials kaapana-ci --token="$(cat /tmp/sa.token)"
kubectl config set-context harvester --cluster=harvester --user=kaapana-ci --namespace=$NS
kubectl config use-context harvester
unset KUBECONFIG
```

Two things that bite here:

- `kaapana-ci-token` must be a Secret of type
  `kubernetes.io/service-account-token` annotated with the ServiceAccount name.
  Kubernetes 1.24+ issues no token Secret by itself, and `kubectl create token`
  expires.
- `SERVER` is the **API server**, not the `server:` line of a Rancher-issued
  kubeconfig. That one points at the proxy, whose certificate the `ca.crt` in
  the Secret does not sign, and kubectl fails with `x509: certificate signed by
  unknown authority`.

Check it, then upload the file as the `HARVESTER_KUBECONFIG` File variable:

```bash
kubectl --kubeconfig /tmp/harvester-ci.kubeconfig auth whoami        # the ServiceAccount
kubectl --kubeconfig /tmp/harvester-ci.kubeconfig -n $NS get vm
kubectl --kubeconfig /tmp/harvester-ci.kubeconfig -n $NS auth can-i --list
```

A playbook that starts making a call outside the table needs that call granted
before it can run in CI.

## 7. Releases

Pushing a protected tag `X.Y.Z` runs a pipeline where `build_packages` swaps
its registry credentials to the protected `RELEASE_REGISTRY_*` variables (via
`rules:variables`) and forces a cold build. Images and charts land in the
release registry tagged `X.Y.Z`.

**Never create `REGISTRY_URL`, `REGISTRY_USER` or `REGISTRY_TOKEN` as project
variables.** A project-level variable silently outranks `rules:variables`, so
their existence breaks the release swap. The CI registry is configured under
the `CI_REGISTRY_*` names instead.

## 8. Project CI/CD variables (secrets)

Only secrets and registry configuration live as project variables
(Settings → CI/CD → Variables); everything else defaults in `.gitlab-ci.yml`.
Do not mirror config values into project variables (see section 7).

`preflight_variables` ([`ci/pipeline/preflight.yml`](pipeline/preflight.yml))
checks at the start of every pipeline that the variables the enabled stages
need are usable — a missing one fails the pipeline in seconds, by name. Add new
required variables there.

| Variable | Masked | Protected | Description |
|---|---|---|---|
| `CI_REGISTRY_URL` | no | no | Registry for CI builds |
| `CI_REGISTRY_USER` | no | no | Username for `CI_REGISTRY_TOKEN`. Shadows a GitLab-predefined variable — if deleted, jobs silently get `gitlab-ci-token`, and `preflight_variables` fails on that value |
| `CI_REGISTRY_TOKEN` | yes | no | Registry push credential; also the default for `GITLAB_API_TOKEN` and `BLABLADOR_API_TOKEN` |
| `RELEASE_REGISTRY_URL` | no | yes | Release registry (release tag pipelines only) |
| `RELEASE_REGISTRY_USER` | no | yes | Release deploy-token username |
| `RELEASE_REGISTRY_TOKEN` | yes | yes | Release deploy-token secret |
| `DOCKER_IO_USER` / `DOCKER_IO_PASSWORD` | no / yes | no | docker.io account (avoids pull rate limits) |
| `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID` | yes / no | no | Failure notifications on develop |
| `KAAPANA_READTHEDOCS_TOKEN` | yes | no | Scheduled docs check |
| `HARVESTER_KUBECONFIG` | File | no | Harvester cluster access; rights it needs in [section 6](#6-runners) |
| `CI_SSH_PRIVATE_KEY` | File | no | SSH key for test VMs (Harvester `kaapana` KeyPair) |
| `DOCKER_AUTH_CONFIG` | no | no | Pull auth for private job images (ci-base) |

Bulk upload from a template:

```bash
cp ci/harvester/control/ci_variables_template.json /tmp/ci_variables.json  # fill in values
python3 ci/harvester/control/set_ci_variables.py \
  --ci-vars-file /tmp/ci_variables.json --dry-run   # drop --dry-run to upload
```

The script cannot set protected variables — create the `RELEASE_REGISTRY_*`
triple manually in the UI.

### `DOCKER_AUTH_CONFIG` and switching registries

`CI_REGISTRY_URL` selects the active registry; runners pulling the ci-base job
image authenticate with `DOCKER_AUTH_CONFIG`:

```json
{"auths":{"registry-1":{"auth":"<base64 user:token>"},"registry-2":{"auth":"<base64 user:token>"}}}
```

- Keep an entry for every registry in rotation, then switching
  `CI_REGISTRY_URL` never breaks image pulls. Adding a registry means adding
  its entry in the same change.
- Each token must be a deploy token with `read_registry` on the GitLab instance
  that owns that registry.
- Missing or mismatched entry: the job dies in *prepare* with `failed to pull
  image … access forbidden`, and the log does **not** show `Authenticating with
  credentials from $DOCKER_AUTH_CONFIG`.
- docker ≥ 28 reads `DOCKER_AUTH_CONFIG` from the job environment too,
  overriding `docker login`. Jobs that push images must `unset
  DOCKER_AUTH_CONFIG` before logging in (the build jobs do). Symptom: `Login
  Succeeded` followed by `denied` on push.
- Environment-scoped variable rows are a parking lot for the inactive
  registry's values; no job declares an `environment`, so only "All (default)"
  rows ever reach a job.

## 9. Adding a job

1. Extend the right template (`.test_template`, `.build_cli_env`,
   `.remote_execution_template`, `.integration_test_local`) — they carry the
   runner tag, image, and rules conventions. `.test_template` caps a single job
   at 5 minutes, so a suite that hits the cap gets split.
2. Needs a CI/CD variable that is not already checked? Add it to
   `preflight_variables`.
3. Gate it with `rules:` on the matching `exec_*` input. The input must be
   declared in the stage file's own `spec:` block and passed down from the
   `include:` block in `.gitlab-ci.yml`.
4. Need docker? Prefer a plain daemonless service; a privileged dind service
   must use the fully-qualified image name (see `task_api_tests`).
5. **Add the job to `if_ci_failing`'s `needs:` list** (`optional: true`;
   `artifacts: true` only if its logs should feed the failure ticket — never
   for jobs whose artifacts contain secrets). If the job uses the test VM,
   **also add it to `destroy_deployment`'s `needs:` list** — that list is the
   teardown barrier.
6. Job talks to anything internal or job-local? Extend `NO_PROXY`/`no_proxy`
   (both casings). A nested `docker build` needs the proxy as a build arg.
7. New dependency between jobs? Declare it in the header of the stage file that
   consumes it.
8. Update this README if the job adds an operational surface.

Check the config before pushing:

```bash
gitlab-ci-local --preview --variable CI_PIPELINE_SOURCE=web   # spec:inputs resolved
gitlab-ci-local --list    --variable CI_PIPELINE_SOURCE=web   # what would run
```

`glab ci lint` cannot do this: it mixes the root config of one ref with the
includes of another, so a `local:` include added on your branch reads as
missing.

## 10. Workflow testcases (`ci-config`)

`run_workflows` collects every YAML document under any
`<chart>/ci-config/*.yaml` as one testcase: the document is the payload for
`kaapana-backend/client/workflow`, and the test passes when the triggered
workflow reaches a successful state. Three fields steer the CI and never reach
the platform:

| Field | Meaning |
|---|---|
| `ci_step: <name>` | the handle of this testcase, what a `ci_after` points at. Unique across all collected files, and only needed on a testcase something else depends on |
| `ci_after: [<name>, …]` | this testcase runs only after those testcases, on the same worker |
| `ci_ignore: true` | collect but do not run. Reported as passed, so it is not usable as a prerequisite |

**Everything is parallel by default.** A testcase without `ci_after` forms a
group of its own, so the workers distribute them freely. Documents of one file
are *not* a sequence: several documents usually mean parameter variants, and
those must stay independent.

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
The order follows the declarations, not the position in the file, so documents
can be reordered freely. The group is named after the alphabetically first
`ci_step` in it and appears in test ids as `test_workflow[dag]@group`.

**What is checked.** A name declared twice, a `ci_after` pointing at a name no
collected testcase declares, and a cycle all abort collection before any
workflow is triggered. At runtime each testcase verifies its prerequisites
succeeded and fails with `prerequisite '<name>' did not run on this worker`
otherwise, so a broken order is never silent.

**`PYTEST_DIST: "loadgroup"` is required** and set on the `run_workflows` job.
The xdist default `load` hands each test to the next free worker and ignores the
group, which would split a group and fail every testcase whose prerequisite ran
elsewhere; collection therefore aborts when a `ci_after` is declared without
`loadgroup`. `loadgroup` guarantees only that a group stays on one worker, not
the order within it — that is why the order comes from the declarations and is
checked at runtime. See the [xdist distribution
modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html). A run
without `-n` needs nothing: one process keeps every group together.

**Limits worth knowing.** A `ci_after` across files only resolves if both files
are collected in the same run, which matters when narrowing with `--files` or
`--test-dir`. And an order says nothing about state: if another testcase
overwrites the tags in between, the prerequisite is still green and the consumer
still fails. Prefer independent testcases over long chains.

Single testcase against a running platform:

```bash
pytest -s ci/ci-code/integration_tests/tests/test_run_workflows.py \
  --host <vm-fqdn> --client-secret <secret> \
  --files data-processing/kaapana-plugin/extension/kaapana-plugin-chart/ci-config/evaluate-segmentations.yaml
```

## Known gaps

- Between the integration test jobs `needs:` order is the only guarantee:
  `first_login` → `install_extensions` → `send_data` → `run_workflows` pass
  platform state along, and no job verifies what it expects to find. Inside
  `run_workflows` the testcases do ([section 10](#10-workflow-testcases-ci-config)).
- A workflow testcase whose DAG the platform does not know counts as passed, so
  a failed extension install can leave `run_workflows` green.
- `install_extensions` and `send_data` carry `retry: 2` — known flakiness.
- `server_installation` raises the kernel `inotify` limits with `sysctl -w`, so
  the raise neither persists across a reboot of the target nor survives being
  overridden by a later installation step. `target_readiness` still warns about
  the instance limit on a target that deployed successfully, which makes that
  check advisory rather than a real requirement.
