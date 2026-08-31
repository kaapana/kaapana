# Running the CI on your own machine

| | Runner Runtime -> Tests, Build, Deploy Coordinator | Deployed | GitLab |
|---|---|---|---|
| [Scenario 1](#scenario-1-run-the-jobs-on-your-machine) | Local | SCI Cloud | yes |
| [Scenario 2](#scenario-2-deploy-the-platform-on-your-machine) | SCI Cloud | Local | yes |
| [Scenario 3](#scenario-3-run-jobs-without-gitlab) | Local | SCI Cloud | no |

1 and 2 are GitLab pipelines: they appear in the UI, keep their logs and
artifacts, and can be retried.

Scenario 1 deployment: the deploy job runs on your
machine but installs the platform wherever `DEPLOYMENT_INSTANCE_FQDN` points, a
fresh Harvester VM by default. Combine it with scenario 2 to get both on your
machine — see [Scenarios 1 and 2 at once](#scenarios-1-and-2-at-once).

## Scenario 1: run the jobs on your machine

### Once: create and register the runner

Needs Maintainer on the project or a gitlab_runner + token. Creating a runner and registering is also possible via UI. However, most reproducible is using `glab api`

The runner agent is itself a container.

1. Create the runner in GitLab using glab in the repository directory:

```bash
TAG=my-workstation
PROJECT_ID=$(glab api /projects/kaapana%2Fkaapana | jq -r .id)

RUNNER_TOKEN=$(printf '{"runner_type":"project_type","project_id":%s,"description":"%s","tag_list":["%s"],"run_untagged":false}' \
    "$PROJECT_ID" "$TAG" "$TAG" \
  | glab api --method POST /user/runners --header "Content-Type: application/json" --input - \
  | jq -r .token)
```

2. Register the runner. One runner takes build, tests and deploy:

```bash
mkdir -p ~/.gitlab-runner
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

`--docker-services_privileged` has that underscore, takes a value, and wants the
`=` form. The dashed spelling is rejected outright; the space-separated form
warns `parameters after this may be ignored`, and the flags after it may
silently not apply.

The config is on your host, so check what actually landed before starting anything:

```bash
grep -vE '^  token' ~/.gitlab-runner/config.toml
```

Three things to look for:

| Expect | Why |
|---|---|
| `volumes` carries `/var/run/docker.sock:/var/run/host-docker.sock` | build jobs reach the host daemon |
| `environment` carries `DOCKER_HOST` | and know where to find it |
| `[[runners]]` appears **once** | registering again appends a second entry instead of replacing the first, and the runner then polls GitLab twice under one token. Delete the stale block by hand if you see two. |

### Why the socket is mounted on that odd path

Build jobs use the host docker daemon, which is what keeps their layer cache
warm across pipelines. `task_api_tests` instead wants its own daemon, and gets
one as a privileged `dind` service.

The two collide if the socket is mounted at the obvious place. `volumes` under
`[runners.docker]` is applied to service containers as well as to the job
container — there is no service-only volume setting. A host socket mounted at
`/var/run/docker.sock` therefore lands inside the `dind` service on exactly the
path its own dockerd needs, and that daemon exits at startup with

```
failed to load listeners: can't create unix socket /var/run/docker.sock: device or resource busy
```

Nothing then listens on `docker:2375`, and `task_api_tests` fails collection
with `[Errno 113] No route to host` — a message three layers downstream of the
cause, so read the **Service container logs** block near the top of the job log
instead.

Mounting at `/var/run/host-docker.sock` leaves `dind` its own path. `--env` then
points build jobs at the host daemon, since they set no `DOCKER_HOST` of their
own and would otherwise find `dind`'s socket or nothing. `task_api_tests` sets
`DOCKER_HOST: tcp://docker:2375` in its job variables
([unit-tests.yml](../pipeline/unit-tests.yml)), and job variables outrank
`environment` from `config.toml`, so it still reaches its own daemon.

The CI runners do not need this: build-01 mounts the socket and runs no
services, tests-01 allows privileged services and mounts no socket — one machine
each, see [inventory.yaml](../harvester/inventory.yaml).

**One caveat on a shared workstation.** `build_packages` runs
`docker system prune --all --volumes -f` when `CI_EXEC_DOCKER_PRUNE=true`
([build.yml](../pipeline/build.yml)). Through the mounted socket that hits your
host daemon: every image no running container holds, and every unused volume,
including this runner's own caches. Leave the variable off unless you mean it.

3. Match the agent-wide cap to that limit. A freshly written config says
   `concurrent = 1`, which caps the runner regardless of its own `limit`:

```bash
sed -i 's/^concurrent = .*/concurrent = 4/' ~/.gitlab-runner/config.toml
```

4. Start it:

```bash
docker run -d --name gitlab-runner --restart always \
  -v ~/.gitlab-runner:/etc/gitlab-runner \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gitlab/gitlab-runner:latest

docker exec gitlab-runner gitlab-runner verify   # must list your runner
glab runner list                                 # your tag, status online
```

`~/.gitlab-runner/config.toml` is yours to edit — `concurrent`, `limit`, extra
volumes. `docker restart gitlab-runner` picks the change up. The same layout as
the CI runners, see
[configure-gitlab-runner.yaml](../harvester/tasks/configure-gitlab-runner.yaml).

Keep `concurrent` and `limit` equal, as the CI runners do
([inventory.yaml](../harvester/inventory.yaml)). `concurrent` always wins, so a
larger `limit` alone only produces `the global concurrent limit will not be
increased and takes precedence`.

### Each run: point stages at your tag

The runner tags are pipeline inputs, so this is per run:

```bash
glab ci run -b my-branch -i tests_runner_tag:e230-pc11
```

| Input | Stage it moves |
|---|---|
| `build_runner_tag` | build, and the CI image rebuild |
| `tests_runner_tag` | unit tests and docs |
| `deploy_runner_tag` | deploy, integration tests, clean |

Set one, two, or all three. Whatever you leave out stays on the shared
runners. The same three fields are on the **Run pipeline** form in the UI.

Watch it with `glab ci status -b my-branch --live`.

### Decommision the runner

```bash
docker stop gitlab-runner
glab runner list
glab api --method DELETE /runners/<id>
docker rm -f gitlab-runner
rm ~/.gitlab-runner/config.toml
```

## Scenario 2: deploy the platform on your machine

### Prepare the target once

Your machine needs:

- **SSH**: the public half of the `CI_SSH_PRIVATE_KEY` file variable (the
  Harvester `kaapana` keypair) in `~/.ssh/authorized_keys` of the user CI will
  log in as.
- **Ports 80, 443 and 11112 free**, and ~80 GiB free under `/var/snap`.
- **microk8s and helm**, with your user in the `microk8s` group. If they are
  missing, CI installs them — see the variable table below — which needs
  passwordless sudo for that user.

Check what is missing without touching anything:

```bash
python3 ci/ci-code/deploy/target_readiness.py
```

Every failed check prints the command that fixes it.

### Run the pipeline

```bash
glab ci run -b my-branch \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.inet.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER \
  --variables CI_EXEC_SERVER_INSTALLATION:false \
  --variables CI_EXEC_REDEPLOY:true \
  --variables CI_EXEC_UNIT_TESTS:false \
  --variables CI_EXEC_INTEGRATION_TESTS:false
```

| Variable | Meaning |
|---|---|
| `DEPLOYMENT_INSTANCE_FQDN` | your machine. Empty means "create a Harvester VM". Max 57 characters |
| `DEPLOYMENT_INSTANCE_USER` | SSH user on it |
| `CI_EXEC_SERVER_INSTALLATION` | `false` for a prepared machine, `true` to let CI install microk8s and helm (needs sudo) |
| `CI_EXEC_REDEPLOY` | default `false`: a platform already on the target fails `target_readiness`, undeploy it yourself. `true` lets the job try the undeploy, which currently leaves releases stuck (kaapana#2293, #2257) |
| `CI_EXEC_UNIT_TESTS`, `CI_EXEC_INTEGRATION_TESTS` | `false` while you only care about the deployment |

A target given by FQDN is never destroyed by the clean stage.

### What you get

| Job | What to look at |
|---|---|
| `target_readiness` | the check table in the log, `target_readiness.json` artifact |
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
  -i deploy_runner_tag:my-workstation \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.inet.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER \
  --variables CI_EXEC_SERVER_INSTALLATION:false \
  --variables CI_EXEC_REDEPLOY:true
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
