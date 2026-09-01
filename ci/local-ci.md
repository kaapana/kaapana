# Running the CI on your own machine

| | Runner Runtime -> Tests, Build, Deploy Coordinator | Deployed | GitLab |
|---|---|---|---|
| [Scenario 1](#scenario-1-run-the-jobs-on-your-machine) | Local | SCI Cloud | yes |
| [Scenario 2](#scenario-2-deploy-the-platform-on-your-machine) | SCI Cloud | Local | yes |
| [Scenario 3](#scenario-3-run-jobs-without-gitlab) | Local | SCI Cloud | no |

1 and 2 are GitLab pipelines: they appear in the UI, keep their logs and
artifacts, and can be retried.

Scenario 1 deployment: the deploy job runs on your machine but installs the
platform wherever the `deployment_fqdn` input points, a fresh Harvester VM by
default. Combine it with scenario 2 to get both on your
machine — see [Scenarios 1 and 2 at once](#scenarios-1-and-2-at-once).

## Scenario 1: run the jobs on your machine

### Once: create and register the runner

Needs Maintainer on the project or a gitlab_runner + token. Creating a runner and registering is also possible via UI. However, most reproducible is using `glab api`
The runner agent is a run from a docker container.

1. Create the runner in GitLab using glab in the repository directory:

```bash
TAG=e230-pc11
PROJECT_ID=$(glab api /projects/kaapana%2Fkaapana | jq -r .id)

RUNNER_TOKEN=$(printf '{"runner_type":"project_type","project_id":%s,"description":"%s","tag_list":["%s"],"run_untagged":false}' \
    "$PROJECT_ID" "$TAG" "$TAG" \
  | glab api --method POST /user/runners --header "Content-Type: application/json" --input - \
  | jq -r .token)
```

2. Seed the agent-wide concurrency limit, `concurrent`. It has to be in the
   file *before* register runs:

```bash
mkdir -p ~/.gitlab-runner
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner --entrypoint sh \
  gitlab/gitlab-runner:latest -c 'printf "concurrent = 4\n" > /etc/gitlab-runner/config.toml'
```

3. Register the runner. One runner takes build, tests and deploy:

```bash
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner \
  gitlab/gitlab-runner:latest register --non-interactive \
  --url https://codebase.helmholtz.cloud --token "$RUNNER_TOKEN" \
  --description "$TAG" --executor docker --limit 4 \
  --docker-image registry.hzdr.de/kaapana/ci-base:v3 \
  --docker-volumes /cache --docker-volumes /builds \
  --docker-volumes /var/run/docker.sock:/var/run/host-docker.sock \
  --docker-services_privileged=true \
  --docker-allowed-privileged-services 'docker.io/library/docker:*' \
  --env DOCKER_HOST=unix:///var/run/host-docker.sock
```

4. Check if the `config.toml` looks correct:
```bash
docker run --rm -v ~/.gitlab-runner:/etc/gitlab-runner:ro --entrypoint sh \
  gitlab/gitlab-runner:latest -c 'grep -vE "^  token" /etc/gitlab-runner/config.toml'
```

Four things to look for:

| Expect | Why |
|---|---|
| `volumes` carries `/var/run/docker.sock:/var/run/host-docker.sock` | build jobs need to reach host daemon |
| `environment` carries `DOCKER_HOST` | and know where to find it |
| `concurrent = 4` on the first line | We want to run unit-tests in parallel |
| `[[runners]]` appears **once** | only a single runner should be register to the instance |

5. Start the agent. Registering only writes the config, nothing polls GitLab
   until this container runs:

```bash
docker run -d --name gitlab-runner --restart always \
  -v ~/.gitlab-runner:/etc/gitlab-runner \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gitlab/gitlab-runner:latest

docker exec gitlab-runner gitlab-runner verify   # lists your runner
glab runner list                                 # your tag, status online
```

`~/.gitlab-runner/config.toml` is bind-mounted, so edits to `concurrent`,
`limit` or the volumes take effect on `docker restart gitlab-runner`.

The socket lands on `/var/run/host-docker.sock` inside jobs because a dind
service needs `/var/run/docker.sock` for itself — the CI runners split those
two roles over two machines, one workstation does both
([ci/README.md section 6](README.md#6-runners)).

**`exec_docker_prune:true` wipes your host docker.** `build_packages` runs
`docker system prune --all --volumes -f` through the mounted socket: every
image no running container holds, and every unused volume, yours included.

### Each run: point stages at your tag

The runner tags are pipeline inputs, so this is per run:

```bash
glab ci run -b my-branch -i tests_runner_tag:e230-pc11 -i build_runner_tag:e230-pc11 -i deploy_runner_tag:e230-pc11
```

| Input | Stage it moves |
|---|---|
| `build_runner_tag` | build, and the CI image rebuild |
| `tests_runner_tag` | preflight, unit tests and docs |
| `deploy_runner_tag` | deploy, integration tests, clean |

Set one, two, or all three. Whatever you leave out stays on the shared
runners. The same three fields are on the **Run pipeline** form in the UI.

Watch it with `glab ci status -b my-branch --live`.

### Reset everything

Removes the docker container running gitlab-runner, every runner GitLab holds under your tag, and the local config:

```bash
TAG=e230-pc11
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

### Prepare the target once

Your machine needs:

- **SSH**: the public half of `CI_SSH_PRIVATE_KEY` (Harvester `kaapana` keypair) placed in `~/.ssh/authorized_keys` for the CI user.
- **Ports 80, 443 and 11112 free**, and ~80 GiB free under `/var/snap`.
- **microk8s and helm**, with your user in the `microk8s` group. If they are
  missing, CI installs them — see the input table below — which needs
  passwordless sudo for that user.

Check what is missing without touching anything:

```bash
python3 ci/ci-code/deploy/target_readiness.py
```

Every failed check prints the command that fixes it.

### Run the pipeline

These are pipeline inputs, so `-i name:value`. The same fields are on the
**Run pipeline** form.

```bash
glab ci run -b my-branch \
  -i deployment_fqdn:my-host.inet.dkfz-heidelberg.de \
  -i deployment_user:$USER \
  -i exec_server_installation:false \
  -i exec_redeploy:true \
  -i exec_unit_tests:false \
  -i exec_integration_tests:false
```

| Input | Meaning |
|---|---|
| `deployment_fqdn` | your machine. Empty means "create a Harvester VM". Max 57 characters |
| `deployment_user` | SSH user on it |
| `exec_server_installation` | `false` for a prepared machine, `true` to let CI install microk8s and helm (needs sudo) |
| `exec_redeploy` | default `false`: a platform already on the target fails `preflight_target`, undeploy it yourself. `true` lets the job try the undeploy, which currently leaves releases stuck (kaapana#2293, #2257) |
| `exec_unit_tests`, `exec_integration_tests` | `false` while you only care about the deployment |

A target given by FQDN is never destroyed by the clean stage.

### What you get

| Job | What to look at |
|---|---|
| `preflight_target` | the check table in the log, `target_readiness.json` artifact |
| `platform_deployment` | `deployment.log`, and `system_check.json` listing every resource and its health |

Then the platform is at `https://<your-fqdn>`. The Keycloak admin password is
printed at the end of the `platform_deployment` log.

### Remove it again

```bash
./kaapanactl.sh deploy --undeploy                 # on the target
./kaapanactl.sh deploy --no-hooks                 # if that hangs or leaves releases
```

## Scenarios 1 and 2 at once

Jobs on your machine and the platform on your machine is just the two command
lines merged:

```bash
glab ci run -b my-branch \
  -i deploy_runner_tag:e230-pc11 \
  -i deployment_fqdn:my-host.inet.dkfz-heidelberg.de \
  -i deployment_user:$USER \
  -i exec_server_installation:false \
  -i exec_redeploy:true
```

The deploy job then runs in a container on your machine and installs the
platform on that same machine over SSH.

## Scenario 3: run jobs without GitLab

[gitlab-ci-local](https://github.com/firecow/gitlab-ci-local) reads
`.gitlab-ci.yml` and runs the job scripts in docker on your machine. No
pipeline, no artifacts in GitLab, no retry button. Fast loop on a job script or
on the config itself.

```bash
npm install -g gitlab-ci-local

gitlab-ci-local --list --variable CI_PIPELINE_SOURCE=web        # what would run
gitlab-ci-local unit_tests --variable CI_PIPELINE_SOURCE=web    # one job
gitlab-ci-local --stage tests --variable CI_PIPELINE_SOURCE=web --privileged
gitlab-ci-local --preview --variable CI_PIPELINE_SOURCE=web     # merged config
```

- `CI_PIPELINE_SOURCE=web` is required. Without it `workflow:rules` falls
  through to `when: never` and nothing runs.
- `--privileged` is only for `task_api_tests` and its dind service.
- Your working tree runs: uncommitted changes to tracked files are included,
  untracked files are not.
- Logs, artifacts and the copied tree land in `.gitlab-ci-local/` (gitignored).
- Off the DKFZ network: `--unset-variable HTTP_PROXY --unset-variable HTTPS_PROXY`.

`--preview` prints the config with `spec:inputs` resolved, so it is how you
check an inputs or include change before pushing. `glab ci lint` cannot: it
mixes the root config of one ref with the includes of another.

This is the tests stage in practice. Build, deploy and test jobs need registry
credentials, the SSH key and a target, so their File-type variables would have
to come from a local `.gitlab-ci-local-variables.yml` — scenario 1 or 2 is the
easier way to run those.
