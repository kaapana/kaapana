# Running the CI on your own machine

| | Runner runtime → tests, build, deploy | Platform deployed on | GitLab pipeline |
|---|---|---|---|
| [Scenario 1](#scenario-1-run-the-jobs-on-your-machine) | your machine | SCI Cloud | yes |
| [Scenario 2](#scenario-2-deploy-the-platform-on-your-machine) | SCI Cloud | your machine | yes |
| [Scenario 1 + 2](#scenarios-1-and-2-at-once) | your machine | your machine | yes |
| [Scenario 3](#scenario-3-run-jobs-without-gitlab) | your machine | — | no |

1 and 2 are real pipelines: they appear in the UI, keep their logs and
artifacts, and can be retried. Scenario 3 runs job scripts in docker with no
GitLab involved.

Everything you steer is a pipeline input — `-i name:value` on the command line,
or the same fields on the **Run pipeline** form. General reference:
[ci/README.md](README.md).

## Scenario 1: run the jobs on your machine

### Once: create and register the runner

Needs Maintainer on the project, or a runner token from someone who has it.

```bash
TAG=my-tag
CI_BASE_IMAGE_TAG=v7
PROJECT_ID=$(glab api /projects/kaapana%2Fkaapana | jq -r .id)

RUNNER_TOKEN=$(printf '{"runner_type":"project_type","project_id":%s,"description":"%s","tag_list":["%s"],"run_untagged":false}' \
    "$PROJECT_ID" "$TAG" "$TAG" \
  | glab api --method POST /user/runners --header "Content-Type: application/json" --input - \
  | jq -r .token)
```

Pick a tag no shared runner uses. Reusing `tests-runner`, `build-runner` or
`deploy-runner` means jobs land on your machine or the Harvester VM at random.

Seed the agent-wide `concurrent` limit — it has to be in the file *before*
`register` runs:

```bash
mkdir -p ~/.gitlab-runner
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner --entrypoint sh \
  gitlab/gitlab-runner:latest -c 'printf "concurrent = 4\n" > /etc/gitlab-runner/config.toml'
```

Register. One runner takes build, tests and deploy, which is why the socket is
mounted at a non-default path ([ci/README.md section 6](README.md#6-runners)):

```bash
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner \
  gitlab/gitlab-runner:latest register --non-interactive \
  --url https://codebase.helmholtz.cloud --token "$RUNNER_TOKEN" \
  --description "$TAG" --executor docker --limit 4 \
  --docker-image "registry.hzdr.de/kaapana/ci-base:$CI_BASE_IMAGE_TAG" \
  --docker-volumes /cache --docker-volumes /builds \
  --docker-volumes /var/run/docker.sock:/var/run/host-docker.sock \
  --docker-services_privileged=true \
  --docker-allowed-privileged-services 'docker.io/library/docker:*' \
  --env DOCKER_HOST=unix:///var/run/host-docker.sock
```

Keep `CI_BASE_IMAGE_TAG` equal to `CI_IMAGES_TAG` in
[`.gitlab-ci.yml`](../.gitlab-ci.yml). A stale tag here only bites jobs that
do not set `image:` themselves.

Check the config:

```bash
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner:ro --entrypoint sh \
  gitlab/gitlab-runner:latest -c 'grep -vE "^  token" /etc/gitlab-runner/config.toml'
```

| Expect | Why |
|---|---|
| `volumes` carries `/var/run/docker.sock:/var/run/host-docker.sock` | build jobs need to reach the host daemon |
| `environment` carries `DOCKER_HOST` | and need to know where it is |
| `concurrent = 4` on the first line | unit tests run in parallel |
| `[[runners]]` appears **once** | a second block means you registered twice |

Start the agent — registering only writes the config, nothing polls GitLab
until this container runs:

```bash
docker run -d --name gitlab-runner --restart always \
  -v ~/.gitlab-runner:/etc/gitlab-runner \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gitlab/gitlab-runner:latest

docker exec gitlab-runner gitlab-runner verify   # lists your runner
glab api "/runners/<ID>"                         # tag_list, paused, projects
```

`~/.gitlab-runner/config.toml` is bind-mounted, so edits to `concurrent`,
`limit`, `pull_policy` or the volumes take effect on
`docker restart gitlab-runner`.

**`exec_docker_prune:true` wipes your host docker.** `build_packages` runs
`docker system prune --all --volumes -f` through the mounted socket: every
image no running container holds, and every unused volume, yours included.

### Each run: point stages at your tag

```bash
glab ci run -b my-branch \
  -i tests_runner_tag:my-tag -i build_runner_tag:my-tag -i deploy_runner_tag:my-tag
```

| Input | Stage it moves |
|---|---|
| `build_runner_tag` | build, and the CI image rebuild |
| `tests_runner_tag` | preflight, unit tests and docs |
| `deploy_runner_tag` | deploy, integration tests, clean |

Set one, two, or all three; whatever you leave out stays on the shared runners.

```bash
glab ci status -b my-branch --live
```

If a job stays pending, the tag does not match a runner registered to *this*
project — `glab api "/runners/<ID>"` shows `tag_list`, `paused` and `projects`.

### Reset everything

Removes the agent container, every runner GitLab holds under your tag, and the
local config:

```bash
TAG=my-tag
PROJECT_ID=$(glab api /projects/kaapana%2Fkaapana | jq -r .id)

docker rm -f gitlab-runner
glab api "/projects/$PROJECT_ID/runners?type=project_type&per_page=100" \
  | jq -r ".[] | select(.description==\"$TAG\") | .id" \
  | xargs -r -I{} glab api --method DELETE /runners/{}
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner --entrypoint sh \
  gitlab/gitlab-runner:latest -c \
  'rm -f /etc/gitlab-runner/config.toml /etc/gitlab-runner/.runner_system_id'
```

## Scenario 2: deploy the platform on your machine

### Prepare the target

Run the readiness check on the target, as the user CI will SSH in as. It is
read-only, needs no sudo, and prints the fixing command for every failure:

```bash
python3 ci/ci-code/deploy/target_readiness.py --domain <your-fqdn>
```

This is the same check `preflight_target` runs in CI, so a clean table here
means the pipeline gets past preflight. It is the authority on what the target
needs — packages, kernel limits, ports, disk, DNS — so there is no second list
to keep in sync.

It cannot check:

- the public half of `DEPLOYMENT_INSTANCE_SSH_KEY` (File-type CI variable) in
  `~/.ssh/authorized_keys` for that user. A provisioned Harvester VM instead
  gets the `kaapana` KeyPair, so that key has to be the matching one
- **passwordless sudo** for that user, needed only when
  `exec_server_installation` is `true`

What the two kinds of target usually fail on:

| Target | Typical failures | Fix |
|---|---|---|
| Fresh Ubuntu VM | microk8s, helm, the `microk8s` group; warns about the inotify instance limit | `exec_server_installation:true` — it installs both and raises the limits |
| Workstation you use for other things | ports 80/443/11112 occupied, a platform already deployed, disk under `/var/snap` | free the ports; undeploy, or `exec_redeploy:true` |
| Target that already ran one deploy | disk under `/var/snap` — the platform images take most of the required minimum, so a target sized at the minimum cannot take a second deploy | undeploy and prune, or give the target a bigger disk |

Run it against a remote target without checking out the repo there — it is
stdlib only:

```bash
ssh <user>@<your-fqdn> 'python3 - --domain <your-fqdn>' \
  < ci/ci-code/deploy/target_readiness.py
```

### Targets with no DNS name

`DEPLOYMENT_INSTANCE_FQDN` gets resolved twice: by ansible inside the job
container, and by whoever opens the platform afterwards. A host only your
workstation can name — an `~/.ssh/config` alias, a `ProxyJump`, an `/etc/hosts`
entry — satisfies neither, and the pipeline has no ProxyJump support anywhere.

Two ways out, cheapest first.

**Put the runner on the target.** Register scenario 1's runner on the target
host itself. The deploy container then reaches the target over the host's own
address, no jump involved, and the build runs on the same machine. Use the
target's IP: a name from the target's `/etc/hosts` does not resolve inside a
job container.

```bash
glab ci run -b my-branch \
  --variables DEPLOYMENT_INSTANCE_FQDN:10.10.10.10 \
  --variables DEPLOYMENT_INSTANCE_USER:ubuntu \
  -i deploy_runner_tag:my-tag -i build_runner_tag:my-tag
```

**Or carry the jump into the job.** Ansible reads `ANSIBLE_SSH_COMMON_ARGS`
from the environment and no job sets it, so a pipeline variable reaches every
deploy job:

```
-o ProxyCommand="ssh -i $DEPLOYMENT_INSTANCE_SSH_KEY -W %h:%p root@<jump-host>"
```

The platform still ends up on a domain nobody outside that network resolves.

### Targets the proxy cannot reach

`NO_PROXY` in [`.gitlab-ci.yml`](../.gitlab-ci.yml) exempts only `localhost`,
`127.0.0.1`, `.dkfz.de`, `.dkfz-heidelberg.de` and the Harvester API. A target
addressed by IP, or on any other domain, is not exempt: every HTTP request the
deploy and test jobs make to it hairpins through `www-int2` and times out. SSH
is unaffected, so `preflight_target` passes and the failure surfaces later.

Add the target to both casings for that run. `--variables` splits its argument
on commas and demands `KEY:VALUE` in every piece, so a `NO_PROXY` list cannot
go through it — use a JSON file and `--variables-from`:

```json
[
  { "key": "DEPLOYMENT_INSTANCE_FQDN", "value": "10.10.10.10", "variable_type": "env_var" },
  { "key": "DEPLOYMENT_INSTANCE_USER", "value": "ubuntu",      "variable_type": "env_var" },
  { "key": "NO_PROXY", "value": "localhost,127.0.0.1,10.10.10.10,.dkfz.de,.dkfz-heidelberg.de,10.129.1.5", "variable_type": "env_var" },
  { "key": "no_proxy", "value": "localhost,127.0.0.1,10.10.10.10,.dkfz.de,.dkfz-heidelberg.de,10.129.1.5", "variable_type": "env_var" }
]
```

```bash
glab ci run -b my-branch --variables-from deploy-vars.json ...
```

Not in a run with `exec_unit_tests:true`. Pipeline variables outrank job
variables, so these would clobber the four job-level exemptions in
[`ci/pipeline/unit-tests.yml`](pipeline/unit-tests.yml) that the dind and
chromium jobs rely on.

### Using your own SSH key

`DEPLOYMENT_INSTANCE_SSH_KEY` is a File-type project variable and the target
must hold its public half. When the target only accepts a key you have locally,
override the variable for that run:

```bash
--variables-file DEPLOYMENT_INSTANCE_SSH_KEY:$HOME/.ssh/kaapana.pem
```

Compare `ssh-keygen -lf ~/.ssh/authorized_keys` on the target against
`ssh-keygen -yf <key> | ssh-keygen -lf -` locally to see whether you need it.


### Run the pipeline

Prepared target — you installed microk8s and helm yourself:

```bash
glab ci run -b my-branch \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.inet.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER \
  -i "exec_server_installation:bool(false)" \
  -i "exec_unit_tests:bool(false)" \
  -i "exec_integration_tests:bool(false)"
```

Bare target — let CI install microk8s and helm (needs passwordless sudo):

```bash
glab ci run -b my-branch \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.inet.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER
```

| Input / variable | Meaning |
|---|---|
| `DEPLOYMENT_INSTANCE_FQDN` | variable, not an input. Your machine. Empty means "create a Harvester VM". Max 57 characters. Must resolve *from inside the job container* — see [Targets with no DNS name](#targets-with-no-dns-name) |
| `DEPLOYMENT_INSTANCE_USER` | variable, not an input. SSH user on it. Defaults to `ubuntu` |
| `exec_server_installation` | `false` for a prepared machine, `true` to let CI install microk8s and helm |
| `exec_redeploy` | `false` makes an existing platform a fatal readiness check; `true` runs `undeploy_platform.yaml` (a plain `kaapanactl.sh deploy --undeploy`) before the deployment. That undeploy still leaves releases stuck sometimes (kaapana#2293, #2257) — the job then fails instead of forcing the removal |
| `exec_unit_tests`, `exec_integration_tests` | `false` while you only care about the deployment |

`glab` sends every `-i` value as a string unless you type it, and the `exec_*`
inputs are declared `boolean` — write `-i "exec_build:bool(false)"`, not
`-i exec_build:false`.

Deploying onto a bare target needs a chart for this commit in the registry, so
either leave `exec_build` at its default or build the commit first. Building
separately keeps a build failure from looking like a deploy failure:

```bash
glab ci run -b my-branch \
  -i build_runner_tag:my-tag \
  -i "exec_build:bool(true)" -i "exec_deploy:bool(false)" \
  -i "exec_unit_tests:bool(false)" -i "exec_integration_tests:bool(false)"
```

### Verify

| Job | What it means, what to read |
|---|---|
| `preflight_target` | ran → the FQDN path was taken. The check table is printed in the job log by `after_script`; there is no artifact |
| `target_readiness` | ran → CI provisioned a VM instead, i.e. `DEPLOYMENT_INSTANCE_FQDN` did not reach the pipeline. Table in the log and in the `target_readiness.log` artifact |
| `prepare_deployment` | logs *using existing deployment target*; no VM created |
| `platform_deployment` | `deployment.log`, and `system_check.json` listing every resource and its health. With `exec_redeploy:true` also `undeploy.log`, written before the deployment starts. The Keycloak admin password is at the end of the log |
| `destroy_deployment` | **absent from the pipeline.** A target given by FQDN is never destroyed by the clean stage |

Then the platform is at `https://<your-fqdn>`.

### Remove it again

On the target:

```bash
./kaapanactl.sh deploy --undeploy      # normal path
./kaapanactl.sh deploy --no-hooks      # if that hangs or leaves releases
```

## Scenarios 1 and 2 at once

Jobs on your machine and the platform on your machine is the two command lines
merged. The deploy job then runs in a container on your machine and installs
the platform onto that same machine over SSH.

```bash
glab ci run -b my-branch \
  -i deploy_runner_tag:my-tag \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.inet.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER \
  -i "exec_server_installation:bool(false)" \
  -i "exec_redeploy:bool(true)"
```

Get scenario 2 green on its own first — otherwise a failure has two candidate
causes.

## Scenario 3: run jobs without GitLab

[gitlab-ci-local](https://github.com/firecow/gitlab-ci-local) reads
`.gitlab-ci.yml` and runs the job scripts in docker on your machine. No
pipeline, no artifacts in GitLab, no retry button. Fast loop on a job script or
on the config itself.

```bash
npm install -g gitlab-ci-local

gitlab-ci-local --preview --variable CI_PIPELINE_SOURCE=web     # merged config
gitlab-ci-local --list    --variable CI_PIPELINE_SOURCE=web     # what would run
gitlab-ci-local unit_tests --variable CI_PIPELINE_SOURCE=web    # one job
gitlab-ci-local --stage tests --variable CI_PIPELINE_SOURCE=web --privileged
```

- `CI_PIPELINE_SOURCE=web` is required. Without it `workflow:rules` falls
  through to `when: never` and nothing runs.
- `--privileged` is only for `task_api_tests` and its dind service.
- Your working tree runs: uncommitted changes to tracked files are included,
  untracked files are not.
- Logs, artifacts and the copied tree land in `.gitlab-ci-local/` (gitignored).
- Off the DKFZ network:
  `--unset-variable HTTP_PROXY --unset-variable HTTPS_PROXY`.

`--preview` resolves `spec:inputs`, so it is how you check an inputs or include
change before pushing. `glab ci lint` cannot: it mixes the root config of one
ref with the includes of another.

This covers the tests stage. Build, deploy and test jobs need registry
credentials, the SSH key and a target, so their File-type variables would have
to come from a local `.gitlab-ci-local-variables.yml` — scenario 1 or 2 is the
easier way to run those.

## Covering the deployment paths

The deploy stage branches on two inputs, and each combination runs a different
job. Worth walking through all of them after touching the deploy stage:

| `DEPLOYMENT_INSTANCE_FQDN` | `exec_server_installation` | Readiness job | Platform lands on | VM destroyed |
|---|---|---|---|---|
| empty | `true` | none | fresh Harvester VM | yes |
| empty | `false` | `target_readiness` (deploy stage) | fresh Harvester VM | yes |
| set | `false` | `preflight_target` (preflight stage) | your host | no |
| set | `true` | none | your host | no |

The two `none` rows have no readiness gate at all, so a target problem first
shows up inside `platform_deployment`. `server_installation` can report success
and the deploy still die on `microk8s status --wait-ready` — ansible runs a
non-interactive shell, and `/snap/bin` is only on its `PATH` if
`/etc/environment` carries a `PATH=` line. Check that before blaming the
install.

Plus `exec_redeploy`, which only matters when a platform is already on the
target. `false` must fail whichever readiness job the row above selected, with
a message telling you to undeploy; `true` demotes that check to a warning and
`platform_deployment` runs `undeploy_platform.yaml` first. Check the target's
free disk before relying on the `true` path — see the table above.

Cheapest order: one tests-only run to confirm the runner tags work, one build,
then the four rows above reusing that build with `exec_build:false`.
