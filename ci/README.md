# Kaapana CI

How to run, debug, and extend the Kaapana CI pipeline.

Configuration lives in [`.gitlab-ci.yml`](../.gitlab-ci.yml) (variables with
defaults and comments) plus one file per stage under
[`ci/pipeline/`](pipeline/). Each stage file's header states what the stage
takes in and hands out — an MR that adds an undeclared dependency must
extend that header.

## 1. What the pipeline does

Test the code → build the platform images → deploy them on a fresh throwaway
VM → test that live deployment → delete the VM.

| Stage | Jobs | Runs on | Duration |
|---|---|---|---|
| `preflight` | `preflight_variables`; `preflight_target` when a target is given by FQDN | tests runner | seconds |
| `tests` | 11 unit-test suites, `ui_e2e_tests` (one job per frontend app), docs build | tests runner | each job 5 min timeout |
| `build` | `build_packages` (+ security scan on nightly) | build runner | hours (warm cache: much less) |
| `deploy` | `prepare_deployment` → `server_installation` or `target_readiness` → `platform_deployment` | deploy runner (Ansible over SSH) | ~1 h |
| `test` | integration tests: login, ports, UI (Playwright), extensions, DICOM data, workflows | deploy runner, against the live VM | 1–3 h |
| `clean` | `destroy_deployment`, `if_ci_failing` | deploy runner | minutes |

Three facts explain most of the design:

- **Every job runs in a fresh container** (docker executor on all runners) —
  nothing persists on the machines; credentials come from File-type CI
  variables.
- **The registry is the only handoff between build and deploy.** Both derive
  the same tag from `git describe`; `prepare_deployment` verifies the chart
  exists (fail-fast, before any VM is created) and hands the tag to later
  jobs via the `deployment.env` dotenv artifact.
- **The test VM is disposable.** `destroy_deployment` deletes it even on
  failure — except externally-provided VMs (never destroyed) or when you
  asked to keep it (see recipes).

## 2. What runs when

| Trigger | What runs |
|---|---|
| Merge request | Full pipeline. `Draft:` MRs run nothing. |
| Push to `develop` | Full pipeline. |
| Nightly schedule | Full pipeline + security scan + ReadTheDocs check. |
| Release tag `X.Y.Z` | Full pipeline, publishing to the release registry with a cold cache ([section 7](#7-releases)). |
| Web UI / API / trigger | Always allowed; you pick the toggles. |

Everything you steer per run is a pipeline **input**, declared in the `spec:`
block at the top of [`.gitlab-ci.yml`](../.gitlab-ci.yml). Set inputs on the
**Run pipeline** form, per schedule, or with `glab ci run -i <name>:<value>`.
A CI/CD variable of the same name has no effect.

| Input | Default | Effect |
|---|---|---|
| `exec_unit_tests` | `true` | tests stage |
| `exec_build` | `true` | build stage |
| `exec_build_arguments` | empty | extra `kaapana-build` flags, e.g. `--latest` |
| `exec_deploy` | `true` | deploy stage |
| `exec_server_installation` | `true` | `false` skips the OS/microk8s install and runs `target_readiness` instead |
| `exec_redeploy` | `false` | `true` undeploys a platform already on the target, `false` fails the job |
| `exec_integration_tests` | `true` | test stage (needs deploy) |
| `exec_security_scan` | `false` | trivy scan of the images this pipeline pushed; flags via `exec_security_scan_arguments` |
| `exec_docker_prune` | `false` | wipe the build cache first (cold, multi-hour build) |
| `exec_destroy_delayed` | `false` | keep the test VM for 4 h after the pipeline |
| `deployment_fqdn` | empty | deploy onto that host instead of a fresh Harvester VM (max 57 chars) |
| `deployment_user` | `ubuntu` | SSH user on that host |
| `build_runner_tag` | `build-runner` | runner tag for the build stage and the CI image |
| `tests_runner_tag` | `tests-runner` | runner tag for the preflight and tests stages |
| `deploy_runner_tag` | `deploy-runner` | runner tag for the deploy, test and clean stages |

`MAINTENANCE` is the one toggle that stays a project variable: `true` pauses
MR, push and schedule pipelines, web and API runs still start.
`ci/utils/trigger_pipeline.py` posts variables only, so it cannot set inputs.

## 3. Recipes

All of these are inputs, so `-i name:value` on the command line or the same
fields on the **Run pipeline** form:

```bash
glab ci run -b my-branch -i exec_build:false -i exec_deploy:false
```

**Unit tests only** — `-i exec_build:false -i exec_deploy:false -i exec_integration_tests:false`

**Build only** — `-i exec_unit_tests:false -i exec_deploy:false -i exec_integration_tests:false`

**Deploy without rebuilding** — `-i exec_unit_tests:false -i exec_build:false`.
Works only if the commit was built and pushed by an earlier pipeline.

**Deploy onto my own VM** — `-i deployment_fqdn:my-host.dkfz-heidelberg.de`
(and `-i deployment_user:<user>` if not `ubuntu`). The FQDN must be ≤ 57 chars
(dcmsend limit) and reachable via SSH with the CI keypair. Such a target is
checked by `preflight_target` and never destroyed by the clean stage. Full
walkthrough in [ci/local-ci.md](local-ci.md).

**Keep the test VM to debug a failure** — re-run with
`-i exec_destroy_delayed:true`. The VM survives 4 h; the delayed
`destroy_deployment` job can be cancelled for longer, or started manually.

**Retrying deploy-stage jobs does NOT re-trigger teardown** — GitLab never
cascades retries, so a `destroy_deployment` that already ran stays in its
old state. If a retried `prepare_deployment` provisioned a VM, retry
`destroy_deployment` manually afterwards (↻ on the job) or the VM leaks.

**SSH into the test VM** — FQDN is in the `prepare_deployment` log/artifact;
the key is the `CI_SSH_PRIVATE_KEY` File variable (matches the Harvester
`kaapana` KeyPair):

```bash
ssh -i <kaapana-key> ubuntu@<vm-fqdn>
```

The platform UI is at `https://<vm-fqdn>`.

**Security scan on demand** — `-i exec_security_scan:true` (with build).
Reports: `security_scan` artifacts (JSON per image), the `security` job's
`vulnerability_report.html`, and GitLab's Security tab.

**Delete a leftover test VM manually** (normally never needed):

```bash
export HARVESTER_KUBECONFIG=~/.kube/harvester.yaml   # File variable holds it
kubectl --kubeconfig $HARVESTER_KUBECONFIG -n kaapana-ci get vm   # ci-<branch>-<sha>
ansible-playbook -i localhost, ci/ci-code/deploy/delete_harvester_vm.yaml -e vm_name=<name>
```

**Pause the CI** — set project variable `MAINTENANCE=true`
(Settings → CI/CD → Variables); remove it to resume.

## 4. When a job is red

Every job uploads its logs/reports as artifacts (job page → Browse) — look
there before re-running. Failures on `develop` automatically create a GitLab
issue with collected logs and post to Slack (`if_ci_failing`). Re-run single
jobs with ↻; you rarely need the whole pipeline.

| Symptom | Likely cause / what to do |
|---|---|
| Unit-test job fails in `pip install` | Dependency change in the component. Reproduce locally — the job runs plain `python:3.12`. |
| `task_api_tests` cannot reach `docker:2375` ("connection refused", or `[Errno 113] No route to host`) | Its dind service died — read the **Service container logs** block near the top of the job log, not the pytest traceback. Two known causes: the service image name must stay **fully qualified** (`docker.io/library/docker:…`), since the privileged-service allowlist matches the literal string; or the runner mounts the host docker socket, which collides with the socket dockerd creates (`device or resource busy`) — see [section 6](#6-runners). |
| Test job times out talking to a service (e.g. `registry:5000`) | DKFZ proxy. The alias must be in `NO_PROXY` **and** `no_proxy` (both casings) in the job variables. |
| `build_packages` fails immediately | Registry login (`CI_REGISTRY_*` variables) or the build VM's docker daemon. Full log in the `build.log` artifact. |
| `build_packages` fails on one image | Read `build.log`; usually reproducible locally with `kaapana-build`. |
| Build very slow | Cold layer cache (`exec_docker_prune`? new build VM?). |
| `prepare_deployment` fails provisioning | Harvester capacity or API — check the job log. |
| `prepare_deployment`: "chart … not found in registry" | The commit was never built. Build it first. |
| Integration test failed, VM already gone | Re-run with `-i exec_destroy_delayed:true`, SSH in (recipe above). |
| `install_extensions` / `send_data` flaky | Known flakiness, `retry: 2` masks most of it. Fails 3× → real; check the JUnit/log artifacts. |
| `playwright_ui_tests` fails | Download the Playwright HTML report artifact — traces and screenshots. |
| Job dies in prepare: `failed to pull image ... ci-base ... access forbidden` | `DOCKER_AUTH_CONFIG` missing an entry for the active registry host, or its token was minted on the wrong GitLab instance ([section 8](#8-project-cicd-variables-secrets)). |
| A stage runs although you switched it off | You set a `CI_EXEC_*` variable. The toggles are inputs, `-i exec_*:false` ([section 2](#2-what-runs-when)). |
| `prepare_deployment`: `... is forbidden: User "..." cannot ...` | `HARVESTER_KUBECONFIG`'s identity lacks that permission ([section 6](#6-runners)). |
| Job stuck "pending" | No runner with the required tag picking it up ([section 6](#6-runners)). |
| Everything fails weirdly after a CI-image change | Tag wasn't bumped — bump `CI_IMAGES_TAG` and re-run ([section 5](#5-the-ci-image-ci-base)). |

## 5. The CI image (`ci-base`)

One tool image for all jobs that need CI tooling:
[`ci/images/ci-base/Dockerfile`](images/ci-base/Dockerfile) (build context
`ci/`, not the repo root). Contains git, docker CLI, helm, trivy, dcmtk,
nmap, ansible, node/npm, chromium, and the pinned Python test dependencies.
Lives at `$CI_REGISTRY_URL/ci-base:$CI_IMAGES_TAG`; rebuilt automatically by
`build_ci_image` when its inputs change.

**The one rule: change the image → bump `CI_IMAGES_TAG` in the same MR.**
Runners pull with `if-not-present`, so re-pushing an existing tag leaves warm
runners on the stale image, silently. With a bump, `build_ci_image` (tests
stage) pushes the new tag before the later stages pull it.

Bootstrap from scratch (empty registry / broken automation):

```bash
docker login $CI_REGISTRY_URL
docker build -f ci/images/ci-base/Dockerfile -t $CI_REGISTRY_URL/ci-base:<tag> ci
docker push $CI_REGISTRY_URL/ci-base:<tag>
```

## 6. Runners

Three runner VMs on Harvester (namespace `kaapana-ci`), defined in
[`ci/harvester/inventory.yaml`](harvester/inventory.yaml). All use the docker
executor.

| Runner | Tag | Special configuration |
|---|---|---|
| kaapana-tests-01 | `tests-runner` | Allows privileged **services** matching `docker.io/library/docker:*` (dind for `task_api_tests`); `/builds` shared between job and services |
| kaapana-build-01 | `build-runner` | Host docker socket mounted into jobs → warm layer cache across pipelines |
| kaapana-deploy-01 | `deploy-runner` | No machine state; credentials from File-type CI variables |

### The two docker modes

- **Host socket** — `build-runner`. Jobs drive the host daemon through a
  bind-mounted `/var/run/docker.sock`. The layer cache survives across
  pipelines and nothing runs privileged. All jobs share that daemon, so
  `docker system prune --all --volumes -f` in `build_packages` is host-wide, a
  job holds root on the host, and `-v` paths in a job's own `docker run` are
  resolved by the host, not inside the job container.
- **dind service** — `tests-runner`, for `task_api_tests`. A privileged
  `docker:28-dind` sidecar per job, reached at `tcp://docker:2375`. State is
  clean per job and nothing leaks onto the host. Its image store starts empty
  every run, so builds are cold without a registry cache; it needs
  `services_privileged`, an allowlist matching the image string literally,
  `DOCKER_TLS_CERTDIR: ""`, and every mounted path under `$CI_PROJECT_DIR`,
  since `/builds` is what job and service share.
- `dind-rootless` is not an alternative: the container still needs
  `--privileged` — only the inner dockerd drops root — and its rootlesskit
  needs unprivileged user namespaces, which Ubuntu 24.04 blocks by default
  (`kernel.apparmor_restrict_unprivileged_userns=1`).
- Build moves into dind once `kaapana-build` restores layers from a BuildKit
  registry cache. The socket mount and its odd path go away with it.

**The tests and build configurations cannot be combined on one runner.**
`volumes` under `[runners.docker]` is applied to service containers as well as
to the job container — there is no service-only volume setting, only
`services_tmpfs`. A mounted host socket therefore lands on
`/var/run/docker.sock` inside the dind service, exactly where its own dockerd
wants to create one, and that daemon exits with

```
failed to load listeners: can't create unix socket /var/run/docker.sock: device or resource busy
```

Nothing then listens on `docker:2375`. So a runner that mounts the socket at
that path cannot take `task_api_tests`. Keep the roles split when adding a
runner to the inventory — the CI VMs have one machine each and no reason to
share.

One machine that has to do both can, by mounting the socket somewhere else
(`/var/run/host-docker.sock`) and pointing build jobs at it with
`environment = ["DOCKER_HOST=unix:///var/run/host-docker.sock"]`. That is how a
workstation runner takes all three stages — see
[ci/local-ci.md](local-ci.md).

Provision / re-provision (also how you add a runner — add it to the
inventory first):

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

The runner agent is a `gitlab/gitlab-runner` container, not an apt package under
systemd. It mounts the host docker socket and creates job containers as siblings
on the host daemon, so bind mounts in `config.toml` resolve against host paths.
The playbook removes a host-installed runner first, so re-provisioning an older
VM converts it.

On-VM troubleshooting, all as `ubuntu` with no sudo:

```bash
docker exec gitlab-runner gitlab-runner verify
docker logs gitlab-runner
docker restart gitlab-runner
grep -vE '^  token' ~/.gitlab-runner/config.toml   # bind-mounted into the container
```

### Harvester access (`HARVESTER_KUBECONFIG`)

The deploy stage needs one credential: a kubeconfig whose identity may make
these calls in `DEPLOYMENT_INSTANCE_HARVESTER_NAMESPACE` (`kaapana-ci`). Nothing
else, and nothing cluster-scoped.

| Resource | Verbs | Used for |
|---|---|---|
| `kubevirt.io` virtualmachines | get, list, watch, create, delete | the test VM, and waiting for it |
| `harvesterhci.io` virtualmachineimages, keypairs | get, list | resolve the boot image by display name, read the SSH public key |
| secrets | get, list, create, patch, delete | the per-VM `<vm>-cloudinit` Secret |
| persistentvolumeclaims | get, list, watch, patch, delete | the root disk: wait for it, own it, delete it |
| `k8s.cni.cncf.io` network-attachment-definitions | get, list | only if `DEPLOYMENT_INSTANCE_NETWORK` names another namespace, as `harvester-public/dkfz-net` does |

With cluster-admin rights on the target cluster, any kubeconfig that covers
that table works — export it, upload it, done.

Without them, make a ServiceAccount in that namespace, have whoever administers
the cluster grant it the table above, and build a kubeconfig from its token —
[the method](https://ryanbaker.io/2021-07-26-svc-acct-kubectl/). The DKFZ side
of that, who to ask and what to send them, is in the Handbook.

Assembling the kubeconfig once the ServiceAccount exists:

```bash
NS=kaapana-ci
SERVER=https://10.129.1.5:6443   # Harvester API server
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

`kaapana-ci-token` is a Secret of type `kubernetes.io/service-account-token`
annotated with the ServiceAccount name: Kubernetes 1.24+ issues no token Secret
by itself, and `kubectl create token` expires. `SERVER` is the API server, not
the `server:` line of a Rancher-issued kubeconfig — that points at the proxy
(`https://sci-cloud.dkfz.de/k8s/clusters/…`), whose certificate the `ca.crt` in
the Secret does not sign, and kubectl fails with `x509: certificate signed by
unknown authority`.

Check it, then upload the file as the `HARVESTER_KUBECONFIG` File variable
([section 8](#8-project-cicd-variables-secrets)):

```bash
kubectl --kubeconfig /tmp/harvester-ci.kubeconfig auth whoami        # the ServiceAccount
kubectl --kubeconfig /tmp/harvester-ci.kubeconfig -n $NS get vm
kubectl --kubeconfig /tmp/harvester-ci.kubeconfig -n $NS auth can-i --list
```

A playbook that starts making a call outside the table needs that call granted
before it can run in CI.

## 7. Releases

Pushing a protected tag `X.Y.Z` runs a pipeline where `build_packages` swaps
its registry credentials to the protected `RELEASE_REGISTRY_*` variables
(via `rules:variables`) and forces a cold build. Images and charts land in
the release registry tagged `X.Y.Z`.

**The precedence trap (broke the 0.7.0 release):** a project-level UI
variable silently outranks `rules:variables`. The release swap only works
because no `REGISTRY_URL`/`REGISTRY_USER`/`REGISTRY_TOKEN` project variables
exist — never create them. The CI registry is configured via the
`CI_REGISTRY_*` names instead.

## 8. Project CI/CD variables (secrets)

Only secrets and registry configuration live as project variables
(Settings → CI/CD → Variables); everything else defaults in
`.gitlab-ci.yml`. Do not mirror config values into project variables (see
the precedence trap above).

The `preflight_variables` job ([`ci/pipeline/preflight.yml`](pipeline/preflight.yml))
checks at the start of every pipeline that the variables the enabled stages
need are usable — a missing one fails the pipeline in seconds, by name. Add new
required variables there.

| Variable | Masked | Protected | Description |
|---|---|---|---|
| `CI_REGISTRY_URL` | no | no | Registry for CI builds |
| `CI_REGISTRY_USER` | no | no | Username for `CI_REGISTRY_TOKEN` (shadows a GitLab-predefined variable — if deleted, jobs silently get `gitlab-ci-token`; `preflight_variables` fails on that value) |
| `CI_REGISTRY_TOKEN` | yes | no | Registry push credential; also the default for `GITLAB_API_TOKEN` and `BLABLADOR_API_TOKEN` |
| `RELEASE_REGISTRY_URL` | no | yes | Release registry (release tag pipelines only) |
| `RELEASE_REGISTRY_USER` | no | yes | Release deploy-token username |
| `RELEASE_REGISTRY_TOKEN` | yes | yes | Release deploy-token secret |
| `DOCKER_IO_USER` / `DOCKER_IO_PASSWORD` | no / yes | no | docker.io account (avoids pull rate limits) |
| `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID` | yes / no | no | Failure notifications on develop |
| `KAAPANA_READTHEDOCS_TOKEN` | yes | no | Scheduled docs check |
| `HARVESTER_KUBECONFIG` | File | no | Harvester cluster access — VM provisioning/deletion; rights it needs: [section 6](#6-runners) |
| `CI_SSH_PRIVATE_KEY` | File | no | SSH key for test VMs (Harvester `kaapana` KeyPair) |
| `DOCKER_AUTH_CONFIG` | no | no | Pull auth for private job images (ci-base) — see below |

**`DOCKER_AUTH_CONFIG` and switching registries.** The CI has used two registries over time , `CI_REGISTRY_URL` selects the active one. 
Runners pulling the ci-base job image authenticate with `DOCKER_AUTH_CONFIG`:

```json
{"auths":{"registry-1":{"auth":"<base64 user:token>"},"registry-2":{"auth":"<base64 user:token>"}}}
```

- Keep an entry for every registry in rotation, then switching `CI_REGISTRY_URL` never breaks image pulls. If you add a new registry, add its entry here in the same change.
- Each token must be a deploy token with `read_registry` on the GitLab instance that owns that registry.
- Symptom of a missing/mismatched entry: job dies in *prepare* with `failed to pull image ... access forbidden`, and the log does **not** show `Authenticating with credentials from $DOCKER_AUTH_CONFIG`.
- docker ≥ 28 reads `DOCKER_AUTH_CONFIG` from the **job environment** too, overriding `docker login`. Jobs that push images must `unset DOCKER_AUTH_CONFIG` before logging in (the build jobs do). Symptom: `Login Succeeded` followed by `denied` on push.
- The environment-scoped variable rows (e.g. `DFKZ_CONTAINER_REGISTRY` / `HIFIS_CONTAINER_REGISTRY` scopes) are not directly used; no job declares an `environment`, so only "All (default)" rows ever reach a job. They serve as a parking lot for the inactive registry's values.

Bulk upload from a template:

```bash
cp ci/harvester/control/ci_variables_template.json /tmp/ci_variables.json  # fill in values
python3 ci/harvester/control/set_ci_variables.py \
  --ci-vars-file /tmp/ci_variables.json --dry-run   # drop --dry-run to upload
```

The script cannot set protected variables — create the `RELEASE_REGISTRY_*`
triple manually in the UI.

## 9. Adding a job

1. Extend the right template (`.test_template`, `.build_cli_env`,
   `.remote_execution_template`, `.integration_test_local`) — they carry the
   runner tag, image, and rules conventions. `.test_template` caps a single
   job at 5 minutes, so a suite that hits the cap gets split into separate
   jobs.
2. Needs a CI/CD variable that is not already checked? Add it to
   `preflight_variables` ([`ci/pipeline/preflight.yml`](pipeline/preflight.yml))
   so a misconfiguration fails in seconds, not in your job.
3. Gate it with `rules:` on the matching `exec_*` input. The input has to be
   declared in the stage file's own `spec:` block and passed down from the
   `include:` block in `.gitlab-ci.yml`.
4. Need docker? Prefer a plain daemonless service; a privileged dind service
   must use the fully-qualified image name (see `task_api_tests`).
5. **Add the job to `if_ci_failing`'s `needs:` list** (`optional: true`;
   `artifacts: true` only if its logs should feed the failure ticket — never
   for jobs whose artifacts contain secrets). If the job uses the test VM,
   **also add it to `destroy_deployment`'s `needs:` list** — that list is
   the teardown barrier.
6. Job talks to anything internal or job-local? Extend `NO_PROXY`/`no_proxy`
   (both casings).
7. New dependency between jobs? Declare it in the header of the stage file
   that consumes it.
8. Update this README if the job adds an operational surface.

## 10. Running the pipeline locally

Three ways, all in [ci/local-ci.md](local-ci.md): register your machine as a
runner and let GitLab schedule real jobs onto it, deploy the platform onto your
machine from a normal pipeline, or run job scripts with no GitLab at all
([gitlab-ci-local](https://github.com/firecow/gitlab-ci-local)).

The last one covers the `tests` stage; build, deploy and test need registry
credentials, Harvester access and a target.

## 11. Workflow testcases (`ci-config`)

`run_workflows` collects every YAML document under any `<chart>/ci-config/*.yaml`
as one testcase: the document is the payload for
`kaapana-backend/client/workflow`, and the test passes when the triggered
workflow reaches a successful state. Three fields steer the CI and never reach
the platform:

| Field | Meaning |
|---|---|
| `ci_step: <name>` | the handle of this testcase, what a `ci_after` points at. Unique across all collected files, and only needed on a testcase something else depends on |
| `ci_after: [<name>, ...]` | this testcase runs only after those testcases, on the same worker |
| `ci_ignore: true` | collect but do not run. Reported as passed, so it is not usable as a prerequisite |

**Everything is parallel by default.** A testcase without `ci_after` forms a
group of its own, so the workers distribute them freely. Documents of one file
are *not* a sequence: several documents usually mean parameter variants
(`validate-dicoms` runs two validators, `download-selected-files` three flag
combinations) and those must stay independent.

**Declare a sequence when a testcase needs state another one produces.**
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

Connected testcases become one xdist group, ordered so that prerequisites run
first. The order follows the declaration, not the position in the file, so
documents can be reordered freely. The group is named after the alphabetically
first `ci_step` in it and appears in test ids as `test_workflow[dag]@group`.

**What is checked.** A name declared twice, a `ci_after` pointing at a name no
collected testcase declares, and a cycle all abort collection before any
workflow is triggered. At runtime each testcase verifies that its prerequisites
did succeed and fails with `prerequisite '<name>' did not run on this worker`
otherwise, so a broken order is never silent. This holds because a group always
runs in one process.

**`PYTEST_DIST: "loadgroup"` is required** and set on the `run_workflows` job.
The xdist default `load` gives each test to the next free worker and never looks
at the group, which would split a group and fail every testcase whose
prerequisite ran on another worker; collection therefore aborts when a
`ci_after` is declared without `loadgroup`. And `loadgroup` guarantees only that
a group stays on one worker, not the order within it, which is why the order
comes from the declarations and is checked at runtime. Scheduling details in the
[xdist distribution
modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html). A run
without `-n` needs nothing: one process keeps every group together and runs it
in collection order.

**Limits worth knowing.** A `ci_after` across files only resolves if both files
are collected in the same run, which matters when narrowing a run with
`--files` or `--test-dir`. And an order says nothing about state: if another
testcase overwrites the tags in between, the prerequisite is still green and the
consumer still fails. Prefer independent testcases over long chains.

Single testcase against a running platform:

```bash
pytest -s ci/ci-code/integration_tests/tests/test_run_workflows.py \
  --host <vm-fqdn> --client-secret <secret> \
  --files data-processing/kaapana-plugin/extension/kaapana-plugin-chart/ci-config/evaluate-segmentations.yaml
```

## Known gaps

- Between the integration test jobs `needs:` order is the only guarantee:
  `first_login` → `install_extensions` → `send_data` → `run_workflows` pass
  platform state along, no job verifies what it expects to find. Inside
  `run_workflows` the testcases do ([section 11](#11-workflow-testcases-ci-config)).
- A workflow testcase whose DAG the platform does not know counts as passed, so a
  failed extension install can leave `run_workflows` green.
- `install_extensions` and `send_data` carry `retry: 2` — known flakiness.
