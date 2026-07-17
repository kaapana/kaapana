# openstack_vm

Provision and delete a Kaapana deployment VM on OpenStack. Formerly part of the
GitLab CI pipeline (removed when the OpenStack infrastructure was deprecated),
kept here as a reusable module of the Ansible deploy library.

## Requirements

```bash
ansible-galaxy collection install openstack.cloud
```

The OpenStack password is read from `~/.os_password` on the machine running the
playbook (never passed via environment or CLI).

## Playbooks

- `provision.yaml` — create the VM (deletes an existing VM of the same name via
  `force_recreate`), wait for SSH, write `deployment.env` with
  `DEPLOYMENT_INSTANCE_FQDN` / `DEPLOYMENT_INSTANCE_USER` to `ARTIFACTS_DIR`.
- `delete.yaml` — delete the VM if it exists.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `OS_AUTH_URL` | both | Keystone auth endpoint |
| `OS_USERNAME` | both | OpenStack user |
| `OS_PROJECT_NAME` | both | OpenStack project |
| `OS_TENANT_ID` | both | OpenStack project ID |
| `OS_IMAGE` | provision | Image name (also selects the SSH user) |
| `OS_INSTANCE_FLAVOR` | provision | Instance flavor |
| `OS_INSTANCE_VOLUME_SIZE` | provision | Root volume size (GB) |
| `OS_KEY_NAME` | provision | Keypair name |
| `OS_NETWORK` | provision | Network name |
| `OS_FLOATING_IP_POOLS` | provision | Floating IP pool |
| `DEPLOYMENT_INSTANCE_VM_NAME` | both | VM name |
| `DEPLOYMENT_INSTANCE_DOMAIN` | provision | Domain appended to the VM name for the FQDN |
| `ORCHESTRATOR_INSTANCE_PRIVATE_SSH_KEY` | provision | Path to the private key for the SSH readiness check |
| `ARTIFACTS_DIR` | provision | Where `deployment.env` is written |

## Usage

```bash
ansible-playbook -i localhost, ci/ansible/openstack_vm/provision.yaml
ansible-playbook -i localhost, ci/ansible/openstack_vm/delete.yaml
```
