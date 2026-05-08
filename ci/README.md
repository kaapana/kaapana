# Kaapana CI/CD Documentation

## CI/CD Pipeline Overview

Kaapana uses **GitLab CI** with five stages across multiple runners:

```mermaid
graph TB
    subgraph "GitLab"
        GH["Pipeline Trigger"]
    end
    
    subgraph UTRVM["Unit Tests Runner VM (Small)"]
        A1["unit_tests"]
        A2["task_api_tests"]
        A3["workflow_api_tests"]
        A4["build_documentation"]
    end
    
    subgraph "Build Runner VM (Large)"
        B["build_packages"]
    end
    
    subgraph "Orchestrator (deploy-runner)"
        C1["prepare_deployment"]
        E["destroy_deployment"]
        F1["if_ci_failing<br/>(on_failure)"]
        F2["security<br/>(if --vulnerability-scan)"]
    end
    
    subgraph DVM["Deployment Instance"]
        C2["server_installation<br/>via SSH"]
        C3["platform_deployment<br/>via SSH"]
        D1["scan_ports<br/>via SSH"]
        D2["first_login<br/>via SSH"]
        D3["install_extensions<br/>via SSH"]
        D4["send_data<br/>via SSH"]
        D5["run_workflows<br/>via SSH"]
    end
    
    GH -->|parallel| A1 & A2 & A3 & A4
    UTRVM -->|all pass| B
    B -->|images ready| C1
    C1 -->|provision/use existing| DVM
    C2 --> C3
    C3 -->|sequentially| D1 --> D2 --> D3 --> D4 --> D5
    D5 -->|if auto-created, delayed in 4 hours| E
    E --> F1
    E --> F2
    
    style A1 fill:#4CAF50,stroke:#2d5016,color:#fff
    style A2 fill:#4CAF50,stroke:#2d5016,color:#fff
    style A3 fill:#4CAF50,stroke:#2d5016,color:#fff
    style A4 fill:#4CAF50,stroke:#2d5016,color:#fff
    style B fill:#2196F3,stroke:#0d47a1,color:#fff
    style C1 fill:#FF9800,stroke:#e65100,color:#fff
    style C2 fill:#FF9800,stroke:#e65100,color:#fff
    style C3 fill:#FF9800,stroke:#e65100,color:#fff
    style D1 fill:#9C27B0,stroke:#4a148c,color:#fff
    style D2 fill:#9C27B0,stroke:#4a148c,color:#fff
    style D3 fill:#9C27B0,stroke:#4a148c,color:#fff
    style D4 fill:#9C27B0,stroke:#4a148c,color:#fff
    style D5 fill:#9C27B0,stroke:#4a148c,color:#fff
    style E fill:#f44336,stroke:#b71c1c,color:#fff
    style F1 fill:#f44336,stroke:#b71c1c,color:#fff
    style F2 fill:#f44336,stroke:#b71c1c,color:#fff
```

### Color Legend
- 🟢 **Green**: Tests stage (unit tests, API tests, documentation)
- 🔵 **Blue**: Build stage (build images)
- 🟠 **Orange**: Deploy stage (prepare deployment, server installation, platform deployment)
- 🟣 **Purple**: Test stage (integration tests)
- 🔴 **Red**: Clean stage (destroy deployment, notifications, security reports)

## Architecture

### Hardware Setup
- **Small VM (tests-runner)**: Runs unit tests and documentation builds in parallel
- **Big VM (build-runner)**: Builds Docker container images
- **Orchestrator (deploy-runner)**: Controls deployment and cleanup flow via Ansible
- **Deployment Instance**: Target server where Kaapana runs (auto-created via Harvester/OpenStack or pre-specified)

### Execution Flow
1. **Tests Stage** (Small VM): Unit/API tests + docs build run **in parallel**
   - Artifacts: `tests/` → uploaded to GitLab
2. **Build Stage** (Big VM): Docker images built
   - Artifacts: `build/build.log`, `build/security-reports/` → uploaded to GitLab
3. **Deploy Stage** (via Orchestrator + SSH):
   - `prepare_deployment`: Provisions or uses existing deployment instance (via Harvester kubeconfig) 
   - `server_installation`: Installs dependencies on deployment instance via SSH
   - `platform_deployment`: Deploys Kaapana via SSH
   - Artifacts: `artifacts/` → uploaded to GitLab
4. **Test Stage** (via Orchestrator + SSH): Each integration test runs sequentially on deployment instance
   - Artifacts: `artifacts/` → uploaded to GitLab
5. **Clean Stage** (via Orchestrator):
   - `destroy_deployment`: Destroys deployment instance (runs **after 4 hours** if auto-provisioned, using Harvester kubeconfig)
   - `if_ci_failing`: Creates issue on develop branch if pipeline fails (runs on failure)
   - `security`: Generates vulnerability report if `--vulnerability-scan` flag used
   - Artifacts: All uploaded to GitLab (1 week retention)

## Setting Up GitLab CI

### Requirements
- Maintainer access to GitLab project
- Harvester Kube config (for VM provisioning)
- GitLab API token

### Setup Steps

1. Clone: `git clone https://codebase.helmholtz.cloud/kaapana/kaapana`

2. Install Ansible and collection:
   ```bash
   sudo apt install ansible -y
   ansible-galaxy collection install openstack.cloud
   ```

3. Set required environment variables for runner provisioning:
   ```bash
   export GITLAB_API_TOKEN="your-gitlab-api-token"
   export GITLAB_PROJECT_ID="your-project-id"
   export GITLAB_URL="https://your-gitlab-instance.com"
   export SSH_PUBLIC_KEY="~/.ssh/kaapana-pub.pem"
   export SSH_PRIVATE_KEY="~/.ssh/kaapana.pem"
   export HARVESTER_KUBECONFIG="~/.kube/harvester.yaml"
   ```
   Or use DOTENV file:
   ```bash
   set -a
   source .env
   set +a
   ```
4. Run ansible-playbook to provision runners:
   ```bash
   cd ci/harvester
   
   # Create build runners
   ansible-playbook create-build-runner-instances.yaml -i inventory.yaml
   
   # Create deploy runners
   ansible-playbook create-deploy-runner-instances.yaml -i inventory.yaml
   
   # Create test runners
   ansible-playbook create-tests-runner-instances.yaml -i inventory.yaml
   
   # Force recreate (deletes and recreates existing instances)
   ansible-playbook create-build-runner-instances.yaml -i inventory.yaml -e force_recreate=true
   ```

### Variables Reference

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `CI_EXEC_UNIT_TESTS` | Bool | `true` | Run unit tests |
| `CI_EXEC_BUILD` | Bool | `true` | Build Docker images |
| `CI_EXEC_SERVER_INSTALL` | Bool | `true` | Install server |
| `CI_EXEC_DEPLOY` | Bool | `true` | Deploy platform |
| `CI_EXEC_INTEGRATION_TESTS` | Bool | `true` | Run integration tests |
| `CI_EXEC_DOCKER_PRUNE` | Bool | `false` | Clean Docker |
| `REGISTRY_URL` | URL | - | Image registry |
| `REGISTRY_USER` | String | - | Registry user |
| `REGISTRY_TOKEN` | String | - | Registry token |
| `DEPLOYMENT_INSTANCE_FQDN` | Host | - | Deployment target |
| `DEPLOYMENT_INSTANCE_USER` | String | ubuntu | SSH user |

---

### TBD

1. Configurable destruction delay -> [start_in does not support CI variable expansion](https://gitlab.com/gitlab-org/gitlab/-/work_items/363069)

## Run CI on custom VM

Run pipeline in the UI and specify: `DEPLOYMENT_INSTANCE_HOSTNAME`

