# fem-adapter: Kaapana as a Tier-3 EUCAIM Federated Data Node

This directory implements Kaapana's side of the integration with EUCAIM's
Federated Execution Manager (FEM): a **Federated Data Node** that receives
federated task submissions from the EUCAIM FEM-orchestrator over RabbitMQ
and executes them as ordinary Kaapana workflows.

It has two parts:

- **`docker/`** -- fem-adapter, a small FastAPI service. It turns each
  `submit_run` FEM-client receives into a Kaapana `Workflow`/`WorkflowRun`
  via `workflow-api`, polls until the run reaches a terminal status, and
  answers back with JSON (FEM-client requires the command it runs to print
  valid JSON to stdout).
- **`fem-client-image/`** -- a Dockerfile that builds the real FEM-client
  (see "What's public vs. what's missing" below) from its public upstream
  source, for the production Helm chart.

Also in this directory:

- **`eucaim-fem-chart/`** -- the Kaapana Extension-Manager Helm chart that
  installs both of the above into a running Kaapana platform.
- **`dev-sandbox/`** -- a self-contained, offline docker-compose harness
  that proves the whole chain end-to-end against the *real* FEM-client
  software and a *real* (test-mode) workflow-api, with no EUCAIM access
  required. See `dev-sandbox/README.md` to run it.

## What's public vs. what's actually missing

The FEM-client **software** is public: `git clone
https://gitlab.bsc.es/fl/fem-client.git` needs no authentication, and
`fem-client-image/Dockerfile` builds it from source, pinned to a specific
commit for reproducibility.

What's still missing -- and genuinely restricted-access, per FEM-client's own
README -- is the **per-federation config repository**,
`{project}-fem-client-config`: the real `config.py` (RabbitMQ host/vhost,
node identity), `json_launcher.json` (how `submit_run` maps to this site's
infrastructure), TLS certificates, and broker credentials. Nobody has handed
us a real example of that repository. Everything under `eucaim-fem-chart/`
and `dev-sandbox/config/` that plays that role is **our own invention**,
built by reading FEM-client's source (`app/receiver.py`,
`app/services/run_tool.py`) to reverse-engineer the schema it expects --
not a copy of, or a claim of conformance with, any real EUCAIM node's
config.

## The fem-adapter REST contract is a working assumption

`POST /fem/submit_run`, `GET /fem/status/{execution_id}`,
`PUT /fem/cancel/{execution_id}` (see `docker/files/app/schemas.py` and
`main.py`) are a contract **we designed**, shaped only by what
`json_launcher.json`'s `submit_run.cmd` can template (task_id, execution_id,
user_id, node_name, sandbox paths, token, and the assembled shell command)
and by what workflow-api needs to create/poll a `WorkflowRun`. It is not a
EUCAIM-specified interface. Expect to revise it once a real
`{project}-fem-client-config` example exists.

## Why `services/federation/`, not `services/base/`

EUCAIM federation participation is site-specific and optional -- most
Kaapana platforms will never install this. It is therefore packaged as an
**Extension-Manager extension** (`eucaim-fem-chart`, `keywords: [
kaapanaapplication, kaapanaexperimental ]`, registered in
`collections/kaapana-collection/requirements.yaml`), not a base service that
every platform runs. `services/federation/` is a new domain directory for
this and future EUCAIM Tier 1/2 components (catalogue, SQL mediator, Beam
proxy).

## eucaim-fem-chart: what it deploys

One Helm release, two Deployments, sharing one release name prefix:

- **`<release>-fem-client`**: the real FEM-client, connecting outward to the
  federation's RabbitMQ broker with the credentials supplied at install
  time.
- **`<release>-fem-adapter`**: this service, reachable from FEM-client (and
  from nowhere else) as `http://<release>-fem-adapter.<namespace>.svc:8090`.

Install-time inputs (node name, RabbitMQ host/port/vhost, `ssl_active`, and
`credentials_node_user` / `credentials_node_password` / three PEM fields for
the CA cert, client cert, and client key) are collected through
`extension_params` in `values.yaml` and rendered into a Kubernetes `Secret`
(`templates/secret.yaml`) -- they never sit in the chart, the ConfigMap, or
either image. The non-secret parts of FEM-client's `config.py` and
`json_launcher.json` are templated into a `ConfigMap`
(`templates/configmap.yaml`) from the same `extension_params`.

Note on the `credentials_` naming convention: it matches how
`custom-registry-chart` names its credential fields
(`credentials_custom_registry_username` etc.). We checked the
extension-manager service and UI and found no code that specially masks or
protects fields with this prefix -- treat it as a naming convention for
operator clarity (this-is-a-secret), not a guaranteed UI masking feature.

Both pods share one PVC (`<release>-sandbox-pv-claim`) mounted at
`/sandbox`, because FEM-client's stage-in/stage-out
(`app/services/data_operations.py`'s `send_files`/`receive_files`) reads and
writes `<sandbox>/<user_id>/<execution_id>/`, and any future bridge that
stages Kaapana outputs back to FEM has to land in that same path. A second,
read-only PVC (`<release>-data-pv-claim`) backs `/data`.  Both follow
`minio-sync-chart`'s hostPath PV/PVC pattern.

**No `/var/run/docker.sock` is mounted anywhere in this chart.**
FEM-client's own Dockerfile installs Docker and docker-compose so it can run
tasks itself via its local "docker" executor; `fem-client-image/Dockerfile`
deliberately leaves that out. In this integration, `json_launcher.json`'s
`submit_run.cmd` only ever curls fem-adapter, which drives workflow-api,
which makes the real workflow engine (Airflow) run the task as an ordinary
Kaapana pod. Giving a federated-task receiver access to the node's container
runtime would let FEM-submitted tasks escape Kubernetes scheduling and
Kaapana's per-project resource limits -- so that access is never granted.
One accepted consequence: FEM-client's own `health-check` action shells out
to `docker --version` and lists local docker images
(`app/services/data_operations.py`'s `pre_checks`); both calls fail (docker
isn't installed) and are caught, surfacing as an `"error"` field in that
action's response rather than crashing anything. This is a known,
intentional deviation from EUCAIM's documented host+Docker deployment
model -- we can't verify whether their Tier-3 acceptance test tolerates it
without access to their orchestrator.

`fem-client` starts as **root** on purpose (no `securityContext` is set):
its `entrypoint.sh` runs under `set -e` and unconditionally does
`groupadd`/`usermod`/`chown -R /app /sandbox` to reconcile the container
user to the `UID`/`GID`/`DOCKER_GID` env vars, then `gosu`-drops to that
user before running `receiver.py`. `DOCKER_GID` is set to a dummy value
(`999`) purely so that `groupadd -g "$DOCKER_GID" docker` succeeds --
without it the container exits immediately on startup. No real docker group
membership is needed since docker.sock is never mounted.

### Known gap: result-staging back into FEM's sandbox layout

Getting `submit_run` to create and track a `WorkflowRun` is solved here.
**Getting the workflow's actual output data back into FEM's expected
layout is not.** Kaapana's workflow outputs land in Kaapana's own storage
(MinIO / Airflow's workflow data dir), not in
`<sandbox>/<user_id>/<execution_id>/`. FEM-client's `send_files` action
(`app/services/data_operations.py:send_files_as_json`) is what the
orchestrator calls to pull a task's results back out, and it only looks in
that sandbox path. Wiring that up -- fem-adapter (or a follow-up task-run
watcher) copying/linking completed-run outputs into
`<sandbox>/<user_id>/<execution_id>/` -- is real, unstarted work. Both
Deployments already mount the shared sandbox PVC in anticipation of it.

## What would need to change for the real EUCAIM broker / e230-pc11

- Obtain the real `{project}-fem-client-config` (or federation-specific
  equivalents of `config.py`/`json_launcher.json`) and install-time values
  (RabbitMQ host, vhost, TLS material, `node_name`) from the EUCAIM/BSC
  federation team, and confirm this fem-adapter REST contract shape
  survives contact with it (`json_launcher.json`'s `submit_run.cmd` may
  need placeholders this prototype doesn't yet resolve, via
  `task_info_vars`/`site_vars`/`system_var_handler` in the real
  `json_launcher.json` -- see `resolve_cmd_placeholders()` in
  FEM-client's `run_tool.py`).
- Set `ssl_active=True` and populate the TLS Secret fields for real.
- Point `FEM_ADAPTER_WORKFLOW_ENGINE=airflow` (already the chart default)
  at a workflow-api backed by the real Airflow, not `DummyAdapter` --
  `FEM_ADAPTER_DUMMY_ENGINE_AUTOCOMPLETE` must stay unset in that
  configuration; it only exists to force workflow-api's test-only
  `DummyAdapter` to a terminal status for the local sandbox.
- Build and solve the result-staging bridge described above.
- Confirm whether EUCAIM's Tier-3 acceptance testing requires FEM-client's
  `health-check`/docker-image-listing action to succeed; if so, this
  integration's decision to omit docker.sock access needs to be revisited
  and re-justified with EUCAIM, not silently worked around.
- This was developed and tested only against the local dev-sandbox
  (docker-compose, `DummyAdapter`) -- never against the real e230-pc11
  Kaapana cluster, its kubectl/helm context, or real Keycloak/Airflow, all
  of which remain untouched by this work.
