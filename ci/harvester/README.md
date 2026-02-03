# Kaapana CI Instance Management

Ansible playbooks for creating and managing Kaapana CI build and deploy instances on Harvester.

## Overview

This setup creates two types of VMs on Harvester for the Kaapana CI/CD pipeline:

- **Build VM** - Compiles containers, builds Helm charts, and packages the platform
- **Deploy VM** - Deploys and tests the Kaapana platform

Each VM runs GitLab runners with a **shared/dedicated** architecture to handle different workload types.

## Runner Architecture

### Shared vs Dedicated Runners

Each VM registers **two runners** with different characteristics:

| Runner Type | Tag | Purpose | Concurrency |
|------------|-----|---------|-------------|
| **Shared** | `build-shared` / `deploy-shared` | Lightweight, parallel jobs | Up to 5 concurrent |
| **Dedicated** | `build-dedicated` / `deploy-dedicated` | Heavy, isolated jobs | 1 at a time |

**When to use which:**
- `*-shared`: Fast jobs like linting, validation, log collection
- `*-dedicated`: Resource-intensive jobs like full builds, platform deployment

### Runner Tags

Use these tags in `.gitlab-ci.yml`:

```yaml
# Build VM runners
build_job:
  tags:
    - build-shared      # For parallel/lightweight build tasks
    # OR
    - build-dedicated   # For heavy builds needing full resources

# Deploy VM runners
deploy_job:
  tags:
    - deploy-shared     # For parallel/lightweight deploy tasks
    # OR
    - deploy-dedicated  # For full platform deployment
```

## Prerequisites

- Python 3.8+
- Ansible 2.18+
- kubectl and Helm 3
- Harvester kubeconfig file
- SSH key pair for VM access
- GitLab Personal Access Token with scopes:
  - `api`, `read_api`, `read_repository`, `write_repository`
  - `create_runner`, `manage_runner`

## Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r target/requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env_template .env
nano .env
```

Required variables:
```bash
HARVESTER_KUBECONFIG="/path/to/harvester.yaml"
SSH_PUBLIC_KEY="/path/to/public.pem"
SSH_PRIVATE_KEY="/path/to/private.pem"
GITLAB_API_TOKEN="glpat-your-token-here"
```

### 3. Configure Instances

Edit `inventory.yaml` to customize:
- VM names and sizes (CPU, memory, disk)
- Runner concurrency settings
- System packages to install

### 4. Create Instances

```bash
# Load environment variables
set -a && source .env && set +a

# Create all instances
ansible-playbook create-instances.yaml

# Create only build instances
ansible-playbook create-instances.yaml --limit build_instances

# Create only deploy instances
ansible-playbook create-instances.yaml --limit deploy_instances

# Force recreate existing instances
ansible-playbook create-instances.yaml -e force_recreate=true
```

## Instance Configuration

### Default VM Sizing (from inventory.yaml)

| Setting | Default | Description |
|---------|---------|-------------|
| `cpu_cores` | 32 | vCPU cores |
| `memory_guest` | 256Gi | RAM |
| `disk_size` | 512Gi | Root disk size |

### Runner Concurrency Settings

**Build VM:**
```yaml
runner_global_concurrent: 6        # Total max concurrent jobs
runner_shared_limit: 5             # Max jobs for shared runner
runner_shared_request_concurrency: 3  # Parallel job requests (reduces pickup latency)
runner_dedicated_limit: 1          # Max jobs for dedicated runner
```

**Deploy VM:**
```yaml
deploy_runner_global_concurrent: 6
deploy_runner_shared_limit: 5
deploy_runner_shared_request_concurrency: 3
deploy_runner_dedicated_limit: 1
```

### Software Installed

**Build VM:**
- Docker (with buildx)
- Helm 3
- Development tools (git, curl, jq, etc.)
- Python 3 with venv

**Deploy VM:**
- Minimal setup (Docker/Helm installed by Kaapana installer)
- Basic tools for CI operations

## Troubleshooting

### Check VM Status
```bash
kubectl --kubeconfig $HARVESTER_KUBECONFIG -n kaapana-ci get vms
kubectl --kubeconfig $HARVESTER_KUBECONFIG -n kaapana-ci get vmi
```

### Get VM IP Address
```bash
kubectl --kubeconfig $HARVESTER_KUBECONFIG -n kaapana-ci get vmi kaapana-build-01 \
  -o jsonpath='{.status.interfaces[0].ipAddress}'
```

### SSH to Instance
```bash
ssh -i $SSH_PRIVATE_KEY ubuntu@<vm-ip>
```

### Check Runner Status
```bash
# On the VM
gitlab-runner status
gitlab-runner list
gitlab-runner verify

# View registered runners in GitLab
# https://codebase.helmholtz.cloud/kaapana/kaapana/-/settings/ci_cd
```

### Runner Not Picking Up Jobs?

1. Check runner is running: `systemctl status gitlab-runner`
2. Verify tags match in `.gitlab-ci.yml`
3. Check runner is online in GitLab CI/CD settings
4. Review runner logs: `journalctl -u gitlab-runner -f`

### Job Pickup Latency

GitLab uses long polling (~50s timeout). With `request_concurrency=1`, worst-case job pickup delay is ~50s. Higher values reduce this:
- `request_concurrency=3` → ~17s max delay
- `request_concurrency=5` → ~10s max delay

## Directory Structure

```
ci/harvester/
├── ansible.cfg              # Ansible configuration
├── inventory.yaml           # Instance definitions and variables
├── create-instances.yaml    # Playbook: create VMs and setup runners
├── .env_template            # Template for environment variables
├── control/                 # Scripts run from control machine
│   └── set_ci_variables.py  # Upload CI variables to GitLab
├── target/                  # Tasks run on target VMs
│   ├── requirements.txt     # Python dependencies
│   ├── install-docker.yaml  # Docker installation tasks
│   ├── install-helm.yaml    # Helm installation tasks
│   ├── register-build-runners.yaml   # Build runner registration
│   ├── register-deploy-runners.yaml  # Deploy runner registration
│   └── configure-gitlab-runners.yaml # Runner configuration
└── vm-templates/            # Helm chart for VM creation
```

## CI Variables

The playbook can optionally upload CI variables to GitLab. Set `upload_ci_variables: true` in inventory.yaml and configure variables in the `ci_variables` section.

Common CI variables:
- `REGISTRY_URL` - Container registry URL
- `REGISTRY_TOKEN` - Registry authentication token
- `DOCKER_IO_USER/PASSWORD` - Docker Hub credentials (for rate limits)
