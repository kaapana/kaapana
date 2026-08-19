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
| `tests` | 8 unit-test suites, docs build | tests runner | minutes |
| `build` | `build_packages` (+ security scan on nightly) | build runner | hours (warm cache: much less) |
| `deploy` | `prepare_deployment` → `server_installation` → `platform_deployment` | deploy runner (Ansible over SSH) | ~1 h |
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

Stage toggles (set per run via **CI/CD → Pipelines → Run pipeline**, or
scripted with `python3 ci/utils/trigger_pipeline.py`):

| Variable | Default | Effect |
|---|---|---|
| `CI_EXEC_UNIT_TESTS` | `true` | tests stage |
| `CI_EXEC_BUILD` | `true` | build stage |
| `CI_EXEC_BUILD_ARGUMENTS` | empty | extra `kaapana-build` flags |
| `CI_EXEC_DEPLOY` | `true` | deploy stage |
| `CI_EXEC_SERVER_INSTALLATION` | `true` | `false` skips the OS/microk8s install — for already-prepared targets |
| `CI_EXEC_INTEGRATION_TESTS` | `true` | test stage (needs deploy) |
| `CI_EXEC_SECURITY_SCAN` | `false` | trivy scan of the built images |
| `CI_EXEC_DOCKER_PRUNE` | `false` | wipe the build cache first (cold, multi-hour build) |
| `CI_EXEC_DESTROY_DELAYED` | `false` | keep the test VM for 4 h after the pipeline |
| `MAINTENANCE` | `false` | project variable; pauses MR/push/schedule pipelines (web/API still work) |

## 3. Recipes

**Unit tests only** — `CI_EXEC_BUILD=false CI_EXEC_DEPLOY=false CI_EXEC_INTEGRATION_TESTS=false`

**Build only** — `CI_EXEC_UNIT_TESTS=false CI_EXEC_DEPLOY=false CI_EXEC_INTEGRATION_TESTS=false`

**Deploy without rebuilding** — `CI_EXEC_UNIT_TESTS=false CI_EXEC_BUILD=false`.
Works only if the commit was built and pushed by an earlier pipeline.

**Deploy onto my own VM** — set `DEPLOYMENT_INSTANCE_FQDN` (and
`DEPLOYMENT_INSTANCE_USER` if not `ubuntu`). FQDN must be ≤ 57 chars (dcmsend
limit) and reachable via SSH with the CI keypair. External VMs are never
destroyed by the clean stage.

**Keep the test VM to debug a failure** — re-run with
`CI_EXEC_DESTROY_DELAYED=true`. The VM survives 4 h; the delayed
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

**Security scan on demand** — `CI_EXEC_SECURITY_SCAN=true` (with build).
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
| `task_api_tests`: "connection refused" to `docker:2375` | Its dind service died. Usual cause: the service image name must stay **fully qualified** (`docker.io/library/docker:…`) — the privileged-service allowlist matches the literal string. |
| Test job times out talking to a service (e.g. `registry:5000`) | DKFZ proxy. The alias must be in `NO_PROXY` **and** `no_proxy` (both casings) in the job variables. |
| `build_packages` fails immediately | Registry login (`CI_REGISTRY_*` variables) or the build VM's docker daemon. Full log in the `build.log` artifact. |
| `build_packages` fails on one image | Read `build.log`; usually reproducible locally with `kaapana-build`. |
| Build very slow | Cold layer cache (`CI_EXEC_DOCKER_PRUNE`? new build VM?). |
| `prepare_deployment` fails provisioning | Harvester capacity or API — check the job log. |
| `prepare_deployment`: "chart … not found in registry" | The commit was never built. Build it first. |
| Integration test failed, VM already gone | Re-run with `CI_EXEC_DESTROY_DELAYED=true`, SSH in (recipe above). |
| `install_extensions` / `send_data` flaky | Known flakiness, `retry: 2` masks most of it. Fails 3× → real; check the JUnit/log artifacts. |
| `playwright_ui_tests` fails | Download the Playwright HTML report artifact — traces and screenshots. |
| Job dies in prepare: `failed to pull image ... ci-base ... access forbidden` | `DOCKER_AUTH_CONFIG` missing an entry for the active registry host, or its token was minted on the wrong GitLab instance ([section 8](#8-project-cicd-variables-secrets)). |
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

On-VM troubleshooting: `sudo gitlab-runner verify`,
`sudo systemctl status gitlab-runner`, config at
`/etc/gitlab-runner/config.toml`.

### Harvester functional user

CI talks to Harvester as the `kaapana-ci` ServiceAccount in the `kaapana-ci`
namespace. The credential is the `HARVESTER_KUBECONFIG` File-type CI variable:
GitLab writes the variable's value into a temp file inside the job container and
sets the variable to that file's *path*, which is what the playbooks hand to the
`kubeconfig:` option of `kubernetes.core.k8s`. Nothing is stored on the runner
VMs — `ci/harvester/tasks/configure-vm-base.yaml` copies no kubeconfig — so
swapping the credential is one variable edit and needs no runner
re-provisioning. Locally the same variable points at your own file:
`export HARVESTER_KUBECONFIG=~/.kube/harvester.yaml`.

**Minting the kubeconfig.** Run these with your own Harvester credential; a
namespace member may create the ServiceAccount and the Secret, but not the RBAC
objects (see below).

```bash
kubectl --kubeconfig ~/.kube/harvester.yaml -n kaapana-ci create serviceaccount kaapana-ci
kubectl --kubeconfig ~/.kube/harvester.yaml apply -f - <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: kaapana-ci-token
  namespace: kaapana-ci
  annotations:
    kubernetes.io/service-account.name: kaapana-ci
type: kubernetes.io/service-account-token
EOF

kubectl --kubeconfig ~/.kube/harvester.yaml -n kaapana-ci get secret kaapana-ci-token \
  -o jsonpath='{.data.ca\.crt}' | base64 -d > /tmp/harvester-ca.crt
TOKEN=$(kubectl --kubeconfig ~/.kube/harvester.yaml -n kaapana-ci get secret kaapana-ci-token \
  -o jsonpath='{.data.token}' | base64 -d)

export KUBECONFIG=/tmp/harvester-ci.kubeconfig
kubectl config set-cluster harvester01 --server=https://10.129.1.5:6443 \
  --certificate-authority=/tmp/harvester-ca.crt --embed-certs=true
kubectl config set-credentials kaapana-ci --token="$TOKEN"
kubectl config set-context harvester01 --cluster=harvester01 --user=kaapana-ci \
  --namespace=kaapana-ci
kubectl config use-context harvester01
unset KUBECONFIG
```

Verify before uploading — `auth whoami` must name the ServiceAccount and every
verb below must answer `yes`:

```bash
export KUBECONFIG=/tmp/harvester-ci.kubeconfig
kubectl auth whoami
for r in "create virtualmachines.kubevirt.io" "delete virtualmachines.kubevirt.io" \
         "list virtualmachineimages.harvesterhci.io" "get keypairs.harvesterhci.io" \
         "create secrets" "patch secrets" "get persistentvolumeclaims" \
         "patch persistentvolumeclaims" "delete persistentvolumeclaims"; do
  printf '%-46s %s\n' "$r" "$(kubectl auth can-i $r -n kaapana-ci)"
done
unset KUBECONFIG
```

Then store it as the File-type variable and remove the local copies:

```bash
glab variable update HARVESTER_KUBECONFIG < /tmp/harvester-ci.kubeconfig   # keeps type File
glab variable set HARVESTER_KUBECONFIG -t file < /tmp/harvester-ci.kubeconfig  # first time
shred -u /tmp/harvester-ci.kubeconfig /tmp/harvester-ca.crt
```

The File type is what makes GitLab materialize the value as a file; as a normal
env var the playbooks would receive YAML where they expect a path. `glab variable
update` has no `--type` flag, so changing an existing variable's type means
`glab variable delete` followed by `glab variable set -t file`. To try a
kubeconfig without touching the stored one, pass it per run instead:
`glab ci run --variables-file HARVESTER_KUBECONFIG:/tmp/harvester-ci.kubeconfig`
— pipeline variables outrank project variables for that pipeline only, and are
readable afterwards through the pipeline's variables API.

**Why the token does not expire.** The token comes from a Secret of type
`kubernetes.io/service-account-token` (`secret/kaapana-ci-token`, annotated
`kubernetes.io/service-account.name: kaapana-ci`). Tokens the API server puts
into such a Secret carry no `exp` claim and stay valid as long as the Secret and
the ServiceAccount exist. Check any time:

```bash
kubectl --kubeconfig ~/.kube/harvester.yaml -n kaapana-ci get secret kaapana-ci-token \
  -o jsonpath='{.data.token}' | base64 -d | cut -d. -f2 | tr '_-' '/+' | base64 -d
```

Do not switch to `kubectl create token` — that is the TokenRequest API, whose
tokens expire (one hour by default) and would need refreshing every pipeline. To
revoke, delete the Secret; to rotate, delete and re-apply it and rebuild the
kubeconfig.

**API server.** The kubeconfig must name `https://10.129.1.5:6443` directly. The
Rancher proxy (`https://sci-cloud.dkfz.de/k8s/clusters/c-zrj95`) resolves only
Rancher credentials of the form `ext/token-xxxxx:secret` and answers a
ServiceAccount token with `User "system:unauthenticated" ...
management.cattle.io`.

The DKFZ proxy is in the way of that endpoint, and `NO_PROXY` cannot get it out
of the way. `www-int2` answers `CONNECT 10.129.1.5:6443` with `403 Forbidden`,
and the python kubernetes client sends the request there: its
`Configuration.__init__` copies `HTTPS_PROXY`/`HTTP_PROXY` out of the
environment, then resets the env-derived `no_proxy` to `None` a few lines later.
The exemption that works is `K8S_AUTH_NO_PROXY`: `kubernetes.core` reads
`K8S_AUTH_*` as its own module options and applies `no_proxy` to the client
*after* construction, where nothing overwrites it. It is a global variable in
`.gitlab-ci.yml`, next to the other proxy settings:

```yaml
K8S_AUTH_NO_PROXY: "10.129.1.5" # Harvester API (harvester01)
```

The playbooks run `hosts: localhost` / `connection: local` and are started as
plain `ansible-playbook` from the job shell, so the job environment is the
module's environment and `kubernetes.core`'s argument-spec fallback reads it
there. Nothing in the playbooks mentions the proxy. A `K8S_AUTH_NO_PROXY`
project variable would override the file (project variables outrank
`.gitlab-ci.yml` — see the precedence trap in section 7); treat that as a
one-off escape hatch and fix the address in the file. Measured against the live
API with a dead proxy in the environment:

| Environment | Result |
|---|---|
| `HTTPS_PROXY` set, nothing else | fails, `ProxyError` |
| `HTTPS_PROXY` + `NO_PROXY=10.129.1.5` | fails, `ProxyError` |
| `HTTPS_PROXY` + `K8S_AUTH_NO_PROXY=10.129.1.5` | succeeds |

Running the playbooks by hand from a proxied workstation needs the same
`export K8S_AUTH_NO_PROXY=10.129.1.5`, since `.gitlab-ci.yml` does not apply
there; `kubectl` against the same endpoint needs `10.129.1.5` in `NO_PROXY`,
which it does honor. The Rancher URL used to work only because the proxy
forwards `sci-cloud.dkfz.de` happily. Symptom when the exemption is missing:
`ProxyError('Unable to connect to proxy', OSError('Tunnel connection failed: 403
Forbidden'))` on the first Harvester task.

**The rights the account needs.** Two bindings, both namespace-scoped, together
covering every call the playbooks make:

- ClusterRole `kubevirt.io:edit`, bound into `kaapana-ci` — the whole
  `kubevirt.io` group. Covers "Apply VM manifest", "Wait for VM to be running",
  "Check if VM exists", "Delete VM and wait for removal".
- Role `kaapana-ci-vm-support` (manifest below) — everything else:
  - `harvesterhci.io/virtualmachineimages` `[get,list,watch]` — "Fetch image by
    label selector" resolves `ubuntu24` to its generated name via
    `harvesterhci.io/imageDisplayName`.
  - `harvesterhci.io/keypairs` `[get,list,watch]` — "Get KeyPair" reads
    `.spec.publicKey` of the `kaapana` KeyPair into the cloud-init userdata.
  - `secrets` `[get,list,create,update,patch,delete]` — the per-VM
    `<vm>-cloudinit` Secret, created before the VM and patched once with an
    `ownerReference` so it is garbage-collected with the VM.
  - `persistentvolumeclaims` `[get,list,watch,update,patch,delete]` — the disk
    PVC is created by Harvester from the `harvesterhci.io/volumeClaimTemplates`
    annotation, so `create` is not needed; the playbooks poll for it, patch the
    `ownerReference`, and delete it explicitly during teardown.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kaapana-ci-vm-support
  namespace: kaapana-ci
rules:
  - apiGroups: [""]
    resources: [secrets]
    verbs: [get, list, create, update, patch, delete]
  - apiGroups: [""]
    resources: [persistentvolumeclaims]
    verbs: [get, list, watch, update, patch, delete]
  - apiGroups: ["harvesterhci.io"]
    resources: [virtualmachineimages, keypairs]
    verbs: [get, list, watch]
```

Both RoleBindings name `subjects: [{kind: ServiceAccount, name: kaapana-ci,
namespace: kaapana-ci}]`; one `roleRef` is `ClusterRole/kubevirt.io:edit`, the
other `Role/kaapana-ci-vm-support`.

**Who can create what.** A namespace member creates serviceaccounts, secrets and
serviceaccount tokens in `kaapana-ci`, and holds no access to RBAC objects at
all: `auth can-i create roles` and `create rolebindings` both answer `no`, and
`get rolebindings` is `Forbidden`. Every rights change therefore goes through an
SCI Cloud admin. Cluster-scoped writes are equally out of reach — `create
clusterroles` answers `no` — but no ClusterRole is needed: `cluster-admin` and
`kubevirt.io:edit` ship with the cluster.

**How this was set up (August 2026).** The ServiceAccount and the token Secret
were created with a namespace member's credentials. The first binding an admin
made was `cluster-admin` (`rolebinding/kaapana-ci-cb`); on harvester01 it had no
effect — `auth can-i --list` returned only the authenticated-principal defaults
(`selfsubjectreviews`, a few read-only `settings.harvesterhci.io`,
`/.well-known/openid-configuration`) and `auth can-i '*' '*'` answered `no` in
every namespace, so that binding lives on another cluster. Then a RoleBinding of
`kubevirt.io:edit` landed, and VM create/get/delete started working while the
playbooks still failed on the image lookup, the keypair, the cloud-init Secret
and the disk PVC — `kubevirt.io:edit` covers the `kubevirt.io` group and nothing
else. Adding `kaapana-ci-vm-support` closed the gap. The account now passes all
nine `auth can-i` checks the script runs, and a `--dry-run=server` VM create —
which goes through Harvester's admission webhooks with the real multus network,
sshName and `volumeClaimTemplates` annotation — is accepted.

**Errors:**

| Symptom | Cause |
|---|---|
| `User "system:unauthenticated" ... management.cattle.io` | The request reached Rancher's proxy. Point the kubeconfig at `https://10.129.1.5:6443`. |
| `auth whoami` succeeds, every `auth can-i` answers `no` | The RoleBinding does not reach this account. Check the cluster and namespace it was created in, and its `roleRef`: Kubernetes accepts a `roleRef` naming a role that does not exist, creating an inert binding with no error and no event. `roleRef` is immutable, so a wrong one is fixed by deleting and recreating the binding. |
| `x509: certificate is valid for ... not <host>` | The kubeconfig names a host instead of `10.129.1.5`. The API cert's SANs are `kubernetes*`, `localhost`, the bare node name `hv-cpu03-20-tp3` and the addresses; `harvester01.dkfz-heidelberg.de` resolves to the VIP but is absent from them. To use a name, either have an admin add the SAN, or set `tls-server-name: kubernetes` in the cluster entry. |
| `Forbidden ... cannot list resource "rolebindings"` | Namespace members hold no read access to RBAC objects. Use `auth can-i` to see what the account may do. |
| Playbook fails at "Fetch image by label selector" with `cannot list ... virtualmachineimages` | `kaapana-ci-vm-support` is missing or unbound. |

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

| Variable | Masked | Protected | Description |
|---|---|---|---|
| `CI_REGISTRY_URL` | no | no | Registry for CI builds |
| `CI_REGISTRY_USER` | no | no | Username for `CI_REGISTRY_TOKEN` (shadows a GitLab-predefined variable — if deleted, jobs silently get `gitlab-ci-token`) |
| `CI_REGISTRY_TOKEN` | yes | no | Registry push credential; also the default for `GITLAB_API_TOKEN` and `BLABLADOR_API_TOKEN` |
| `RELEASE_REGISTRY_URL` | no | yes | Release registry (release tag pipelines only) |
| `RELEASE_REGISTRY_USER` | no | yes | Release deploy-token username |
| `RELEASE_REGISTRY_TOKEN` | yes | yes | Release deploy-token secret |
| `DOCKER_IO_USER` / `DOCKER_IO_PASSWORD` | no / yes | no | docker.io account (avoids pull rate limits) |
| `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID` | yes / no | no | Failure notifications on develop |
| `KAAPANA_READTHEDOCS_TOKEN` | yes | no | Scheduled docs check |
| `HARVESTER_KUBECONFIG` | File | no | Harvester cluster access — VM provisioning/deletion; kubeconfig of the `kaapana-ci` ServiceAccount ([section 6](#harvester-functional-user)) |
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
   runner tag, image, and rules conventions.
2. Gate it with `rules:` on the matching `CI_EXEC_*` toggle.
3. Need docker? Prefer a plain daemonless service; a privileged dind service
   must use the fully-qualified image name (see `task_api_tests`).
4. **Add the job to `if_ci_failing`'s `needs:` list** (`optional: true`;
   `artifacts: true` only if its logs should feed the failure ticket — never
   for jobs whose artifacts contain secrets). If the job uses the test VM,
   **also add it to `destroy_deployment`'s `needs:` list** — that list is
   the teardown barrier.
5. Job talks to anything internal or job-local? Extend `NO_PROXY`/`no_proxy`
   (both casings).
6. New dependency between jobs? Declare it in the header of the stage file
   that consumes it.
7. Update this README if the job adds an operational surface.

## 10. Running the pipeline locally

The `tests` stage runs on any machine with docker — no runner, no GitLab —
via [gitlab-ci-local](https://github.com/firecow/gitlab-ci-local)
(`npm install -g gitlab-ci-local`). From the repo root:

```bash
# everything the tests stage runs in CI (9 jobs)
gitlab-ci-local --stage tests --variable CI_PIPELINE_SOURCE=web --privileged

# a single job
gitlab-ci-local unit_tests --variable CI_PIPELINE_SOURCE=web

# see which jobs would run
gitlab-ci-local --list --variable CI_PIPELINE_SOURCE=web
```

- `CI_PIPELINE_SOURCE=web` is required — without it `workflow:rules` falls
  through to `when: never` and no jobs match.
- `--privileged` is only needed for `task_api_tests` (its dind service);
  drop it when running other jobs individually.
- Jobs run against your **working tree**: uncommitted changes to tracked
  files are included, untracked files are not.
- Logs, artifacts, and the copied tree land in `.gitlab-ci-local/`
  (gitignored).
- The global variables bake in the DKFZ proxy. Off the DKFZ network, drop
  it: `--unset-variable HTTP_PROXY --unset-variable HTTPS_PROXY`.
- Only the `tests` stage is meant to run locally — build/deploy/test/clean
  need registry credentials, Harvester access, and a test VM.

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
- `ci/docs/local-ci.md` predates the current variable set (it references
  variables that no longer exist) — for local runs use
  [section 10](#10-running-the-pipeline-locally) instead.
