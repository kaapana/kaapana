# Deploy on your own machine (or any ssh-reachable host)

The deploy stage is four ansible playbooks over SSH. Run them from your
checkout against your workstation or any host you can reach, no GitLab and no
runner. CI runs the same files with the same variables.

## 1. What the target needs

- SSH: your public key in the `authorized_keys` of the user you connect as.
- Either an already prepared machine (microk8s, helm, jq, user in the `microk8s`
  group) — then skip step 3 — or sudo rights for the server installation.
- 80, 443 and 11112 free, and ~80 GiB free under `/var/snap`.

Step 2 tells you which of these are missing, so start there.

## 2. Check the target

```bash
export VM_FQDN=my-host.example.org        # deployment target
export VM_USER=$USER                      # SSH user on the target
export SSH_KEY=~/.ssh/kaapana.pem         # key matching authorized_keys
export ARTIFACTS_DIR=$PWD/artifacts       # where the reports land
export ANSIBLE_HOST_KEY_CHECKING=False
mkdir -p "$ARTIFACTS_DIR"

ansible-playbook ci/ci-code/deploy/target_readiness.yaml \
  -i "$VM_FQDN," -u "$VM_USER" --private-key "$SSH_KEY"
```

This is the `target_readiness` CI job. It changes nothing and needs no sudo.
It prints a table, writes `artifacts/target_readiness.json`, and names the
command that fixes each failed check.

Sitting in front of the machine? Run the check directly, no ansible:

```bash
python3 ci/ci-code/deploy/target_readiness.py            # table on stdout
python3 ci/ci-code/deploy/target_readiness.py --report report.json --log table.txt
```

## 3. Prepare the target (skip if step 2 says READY)

Needs sudo on the target — installs microk8s and helm and puts your user in the
`microk8s` group:

```bash
ansible-playbook ci/ci-code/deploy/server_installation.yaml \
  -i "$VM_FQDN," -u "$VM_USER" --private-key "$SSH_KEY"
```

It re-runs the readiness check at the end.

## 4. Deploy the platform

```bash
export CI_PROJECT_DIR=$PWD
export REGISTRY_URL=<registry>/<project>   # where the chart lives
export REGISTRY_USER=<user>
export REGISTRY_TOKEN=<token>
export VERSION_TAG=$(git describe --tags --always)
export DEPLOYMENT_INSTANCE_PLATFORM_PREFIX=local-dev
export CI_EXEC_REDEPLOY=true               # replace a platform already there

ansible-playbook ci/ci-code/deploy/deploy_platform.yaml \
  -i "$VM_FQDN," -u "$VM_USER" --private-key "$SSH_KEY"
```

`VERSION_TAG` must exist in the registry — check before waiting an hour:

```bash
helm registry login "${REGISTRY_URL%%/*}" -u "$REGISTRY_USER" -p "$REGISTRY_TOKEN"
helm show chart "oci://$REGISTRY_URL/kaapana-admin-chart" --version "$VERSION_TAG"
```

A platform already on the target is undeployed first when
`CI_EXEC_REDEPLOY=true`; with `false` the playbook stops and names the platform
prefix it found. Results: `artifacts/deployment.log`, `artifacts/undeploy.log`, and the
health of every resource in `artifacts/system_check.json`.

## 5. Test the deployment

```bash
ansible-playbook ci/ci-code/integration_tests/remote_execution/setup_integration_tests.yaml \
  -i "$VM_FQDN," -u "$VM_USER" --private-key "$SSH_KEY"
source "$ARTIFACTS_DIR/integration_test_setup.env"      # CLIENT_SECRET

pip install -e ci/ci-code/integration_tests
python3 -m pytest -s ci/ci-code/integration_tests/tests/test_first_login.py \
  --host "$VM_FQDN" --client-secret "$CLIENT_SECRET"
```

## 6. The same thing from GitLab

Run the pipeline with:

| Variable | Value |
|---|---|
| `DEPLOYMENT_INSTANCE_FQDN` | your target (≤ 57 chars, never destroyed by the clean stage) |
| `DEPLOYMENT_INSTANCE_USER` | SSH user on it |
| `CI_EXEC_SERVER_INSTALLATION` | `false` if the target is prepared — `target_readiness` runs instead |
| `CI_EXEC_REDEPLOY` | `true` to replace a platform already on the target |

The CI key is the `CI_SSH_PRIVATE_KEY` file variable, so that public key has to
be in the target's `authorized_keys`.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `Permission denied (publickey)` | key not in the target's `authorized_keys`, or wrong `-u` |
| readiness: `microk8s not found` | unprepared target — run step 3 |
| readiness: `user is not a member of the microk8s group` | `sudo usermod -a -G microk8s $USER`, then reconnect |
| readiness: `ports already in use` | something else listens on 80/443/11112 (`sudo ss -ltnp`) |
| readiness: NodePort range | add `--service-node-port-range=80-32000` to `/var/snap/microk8s/current/args/kube-apiserver`, restart microk8s |
| deploy: `Project already deployed` | run with `CI_EXEC_REDEPLOY=true`, or `./kaapanactl.sh deploy --undeploy` on the target |
| undeploy hangs or leaves releases | `./kaapanactl.sh deploy --no-hooks` on the target |
