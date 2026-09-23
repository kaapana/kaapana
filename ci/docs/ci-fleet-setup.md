# CI runner fleet (Harvester)

**Prerequisites:** Python 3 (typer + requests) and Ansible ≥ 7 with `community.general` & `kubernetes.core` collections.

## Installation


```bash
curl http://$(hostname -I | awk '{print $1}'):9252/metrics
```


```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ci/harvester/tasks/requirements.txt
ansible-galaxy collection install community.general kubernetes.core
```

*Current setup → explore the fleet with `ci_fleet.py status`*

The CI runners are GitLab runner agents on Harvester VMs. The fleet is
declared in [inventory.yaml](../ci/harvester/inventory.yaml) and managed declaratively by
[ci_fleet.py](../ci/harvester/ci_fleet.py): edit the inventory and re-run the ci_fleet.py commands explained below.

## One-time setup

**`.env`** — gitignored, read directly by `inventory.yaml` and `ci_fleet.py`
(no exporting, no sourcing).

| Key | What it is |
|---|---|
| `GITLAB_URL` | GitLab instance base URL |
| `GITLAB_API_TOKEN` | API token allowed to manage the project's runners |
| `GITLAB_PROJECT_ID` | numeric id of the project the runners register to |
| `SSH_PRIVATE_KEY` | path to the private key of the Harvester keypair — the VMs accept only this key |
| `HARVESTER_KUBECONFIG` | path to a kubeconfig with access to the `kaapana-ci` namespace |
| `RUNNERS_PAUSED` | optional, `true` registers the runners paused so a new VM can be inspected before it takes jobs |

## CI fleet commands

```bash
ci_fleet.py list                        # declared fleet: what inventory.yaml says
ci_fleet.py status                      # live state: VMs, registered runners, versions, drift
ci_fleet.py up                          # converge: create missing VMs, re-apply roles
ci_fleet.py up --force                  # destroy and rebuild everything declared
ci_fleet.py up --hosts kaapana-ci-01    # converge only the named VMs
ci_fleet.py down --hosts kaapana-ci-01  # destroy named VMs, unregister their runners
```

- **Adding a runner is an inventory edit.** Add a VM under `ci_instances` — or
  a role to an existing VM's `runners:` list — then `up`.
- **`up` always converges.** `config.toml` is rebuilt from scratch on every
  run, so a role removed from the inventory disappears from the VM; `--force`
  additionally wipes disk and cloud-init state for a true from-scratch rebuild.
- **`down` requires `--hosts` on purpose** — a fleet is never destroyed by
  accident. Unregistered runners left in GitLab show up under `status`.

On a runner VM the agent runs **user-mode** as `ubuntu`:

```bash
systemctl --user status gitlab-runner
cat ~/.gitlab-runner/config.toml
```

## Monitoring Export

- **Node and container metrics** — node-exporter on port **9100** and cAdvisor
  on port **8081**, installed by `tasks/install-monitoring.yaml` on every fleet
  VM. A separate MR provides the scrape server that consumes them.
- **GitLab-runner metrics** — exposed on port **9252** (`runner_metrics_port`).