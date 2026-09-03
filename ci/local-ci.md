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
  --docker-image registry.hzdr.de/kaapana/ci-base:<tag> \
  --docker-volumes /cache --docker-volumes /builds \
  --docker-volumes /var/run/docker.sock:/var/run/host-docker.sock \
  --docker-services_privileged=true \
  --docker-allowed-privileged-services 'docker.io/library/docker:*' \
  --env DOCKER_HOST=unix:///var/run/host-docker.sock
```

Take `<tag>` from `CI_IMAGES_TAG` in [`.gitlab-ci.yml`](../.gitlab-ci.yml).

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

Two things it cannot check for you:

- the public half of `CI_SSH_PRIVATE_KEY` (Harvester `kaapana` KeyPair) in
  `~/.ssh/authorized_keys` for that user
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

### Run the pipeline

Prepared target — you installed microk8s and helm yourself:

```bash
glab ci run -b my-branch \
  -i deployment_fqdn:my-host.inet.dkfz-heidelberg.de \
  -i deployment_user:$USER \
  -i exec_server_installation:false \
  -i exec_unit_tests:false \
  -i exec_integration_tests:false
```

Bare target — let CI install microk8s and helm (needs passwordless sudo):

```bash
glab ci run -b my-branch \
  -i deployment_fqdn:my-host.inet.dkfz-heidelberg.de \
  -i deployment_user:$USER
```

| Input | Meaning |
|---|---|
| `deployment_fqdn` | your machine. Empty means "create a Harvester VM". Max 57 characters |
| `deployment_user` | SSH user on it |
| `exec_server_installation` | `false` for a prepared machine, `true` to let CI install microk8s and helm |
| `exec_redeploy` | `false` fails `preflight_target` when a platform is already there; `true` lets the job undeploy it first, which currently leaves releases stuck (kaapana#2293, #2257) |
| `exec_unit_tests`, `exec_integration_tests` | `false` while you only care about the deployment |

Deploying onto a bare target needs a chart for this commit in the registry, so
either leave `exec_build` at its default or build the commit first.

### Verify

| Job | What it means, what to read |
|---|---|
| `preflight_target` | ran → the FQDN path was taken. The check table in the log, `target_readiness.json` artifact |
| `target_readiness` | ran → CI provisioned a VM instead, i.e. `deployment_fqdn` did not reach the pipeline |
| `prepare_deployment` | logs *using existing deployment target*; no VM created |
| `platform_deployment` | `deployment.log`, and `system_check.json` listing every resource and its health. The Keycloak admin password is at the end of the log |
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
  -i deployment_fqdn:my-host.inet.dkfz-heidelberg.de \
  -i deployment_user:$USER \
  -i exec_server_installation:false \
  -i exec_redeploy:true
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

| `deployment_fqdn` | `exec_server_installation` | Readiness job | Platform lands on | VM destroyed |
|---|---|---|---|---|
| empty | `true` | none | fresh Harvester VM | yes |
| empty | `false` | `target_readiness` (deploy stage) | fresh Harvester VM | yes |
| set | `false` | `preflight_target` (preflight stage) | your host | no |
| set | `true` | none | your host | no |

Plus `exec_redeploy`, which only matters when a platform is already on the
target: `false` must fail `preflight_target` with a message telling you to
undeploy, `true` must attempt the undeploy itself. Check the target's free disk
before relying on the `true` path — see the table above.

Cheapest order: one tests-only run to confirm the runner tags work, one build,
then the four rows above reusing that build with `exec_build:false`.
