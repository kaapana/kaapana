# kaapana-ci

## Some general concepts of GitLab CI/CD

Core concepts of Gitlab CI

* pipelines
* stages
* jobs
* variables
* dependencies
* artifacts

### What is a gitlab-runner?

A gitlab-runner is a service that is associated with a gitlab project and continuously fetches ci jobs from this project. 
The gitlab-runner executes these jobs on its host instance, i.e. the *CI-instance*.

### What is the ci-instance and what is the deployment-instance?

* ***ci-instance***: The instance where the gitlab-runner is hosted and where the build is executed.
* ***deployment-instance***: The instance where the platform is deployed.
* Build script is executed on the ***ci-instance***
* Logs are persisted on the ***ci-instance***

The CI-instance mainly hosts the gitlab-runner who executes all jobs specified in `gitlab-ci.yml`. 
Most of the jobs consist of an ansible playbook. 
The tasks in these playbooks are either executed directly on the ci-instance or on the remote *deployment-instance*. 
A deployment-instance is used to deploy a Kaapana platform.

### How to setup the Kaapana continuous integration?

#### Requirements for setting up the CI

* At least maintainer access to a Kaapana project on gitlab.
* Openstack user credentials.
* Gitlab registration token to register the gitlab-runner. You get them, when you create a new GitLab runner in your GitLab project.
* Gitlab api-token to upload the default CI variables.

#### Steps to setup the CI

1. Clone the repository from [https://codebase.helmholtz.cloud/kaapana/kaapana-ci](https://codebase.helmholtz.cloud/kaapana/kaapana-ci)
2. Install the dependencies:

    * **Install Ansible**
        * Ubuntu/Debian

          ```bash
          sudo apt update
          sudo apt install ansible -y
          ```

        * CentOS/RHEL

          ```bash
          sudo yum install epel-release -y
          sudo yum install ansible -y
          ```

    * **Install the Required Ansible Collection ( `openstack.cloud.server`)**

        ```bash
        ansible-galaxy collection install openstack.cloud
        ```

3. Create `setup_vars.yaml` from `setup_vars_template.yaml` in `file_templates/` and specify all variables according to your setup.
    This file contains parameters required to create and setup the ci-instance
    ```bash
    cp file_templates/setup_vars_template.yaml file_templates/setup_vars.yaml
    ```
4. Create `ci-settings.yaml` from `ci-settings-template.yaml` in `file_templates/` and specify all variables according to your setup.
    This file should contain the default values for the CI variables in your project.
    ```bash
    cp file_templates/ci-settings-template.yaml file_templates/ci-settings.yaml
    ```
5. Run the `ci-code/setup_playbooks/setup_ci.yaml`.
6. SSH to the kaapana-ci instance
7. On the ci-instance, there should be a file `$HOME/.gitlab-runner/config.toml`
8. This file should contain a section similar to the one below. 
    Make sure, that the subsection `[runners.custom_build_dir]` exists.
      ```bash
      [[runners]]
        name = "shell-runner"
        url = "..."
        id = ...
        token = "..."
        token_obtained_at = ...
        token_expires_at = ...
        executor = "shell"
        [runners.cache]
          MaxUploadedArchiveSize = 0
        [runners.custom_build_dir]
          enabled = true
      ```

9. Start the gitlab-runner service in the background `nohup gitlab-runner run </dev/null &>/dev/null &`
10. Check if everything works, by triggering a web-pipeline in your GitLab project.

The playbook at `ci-code/setup_playbooks/setup_ci.yaml` automates the following steps to get your ci instance up and running:

1. Launch an openstack instance
2. Upload default CI variables into the project settings
3. Store the password for the openstack user for future communication with the openstack API
4. Install proxy
5. Setup timeserver
6. Upgrade and install apt packages
7. Install required pip packages
8. Adjust user PATH variable
9. Install required ansible collections
10. Copy ssh key to the ci-instance for accessing deployment instances
11. Install docker and helm
12. Install and register gitlab-runner
13. Create directory in `/etc/` for ansible

## Directory structure

```bash
.
├── ci-code                 # Playbook and code that is executed during a CI pipeline
│   ├── build               # Code for the build-stage
│   ├── clean               # Code for the last stage
│   ├── deploy              # Code for the platform deployment
│   │   └── tasks
│   ├── prepare             # Code for the preparation stage
│   └── test                # Code for the test stage
│       ├── jobs            # Ansible playbooks for each job of the test stage
│       │   ├── extensions  # Install all extensions
│       │   ├── integration_tests   # Trigger some workflows based on .yaml files in the repository
│       │   ├── testdata    # Download testdata and send to dicom via dcmsend
│       │   └── ui_tests    # Python code for selenium test, currently only first login to the platform.
│       └── src             # python code for the test stage
│           └── base_utils  # Common python utilities for the jobs in the test stage
├── setup_playbooks ### Playbooks and code to setup the CI-instance
│   ├── file_templates
│   └── task_templates
└── templates               # Place for child-pipelines or templated parts of the .gitlab-ci.yml config.
```

## Variables

A short description of all variables and where they can be configured

| Variable name | Default| Values | Comment |
| --- | --- | --- | --- |
| **Deployment instance** | | |
| DEPLOYMENT_INSTANCE_IP | `"none"` | `["none", <ip-address>]` | The ip address of an existing instance that should be used as deployment instance. If not specified and `OS_CREATE` is `false` the pipeline will fail. |
| DEPLOYMENT_INSTANCE_NAME | `kaapana_ci_default` | | The name of the deploymen-instance as ansible groupname and in openstack.|
| DEPLOYMENT_INSTANCE_USER | `ubuntu` | |  The username on the deployment instance |
| HTTP_PROXY | | | URL to http proxy server on the ***deployment-instance*** |
| HTTPS_PROXY | | |  URL to https proxy server on the ***deployment-instance*** |
| **Openstack** | | |
| OS_DELETE | `false` | `["true","false"]` |  If set to "true" the openstack instance  corresponding to `DEPLOYMENT_INSTANCE_NAME` will be deleted at the beginning of the pipeline.
| OS_CREATE | `true` | `["true","false"]` | If set to "true" a new openstack instance will be created with name `DEPLOYMENT_INSTANCE_NAME` as hostname.
| OS_AUTH_URL | | |  URL for authentification with the openstack API
| OS_PROJECT_NAME | | | Name of the openstack project where the ***deployment-instance*** should be hosted
| OS_INSTANCE_FLAVOR | | |  Flavor for the openstack instance
| OS_KEY_NAME | | | Key name for the openstack instance
| OS_IMAGE | | | Image used for the openstack image
| OS_TENANT_ID | | | Project ID of the openstack project corresponding to `OS_PROJECT_NAME`
| OS_USERNAME | | | Openstack username used to spawn ***deployment-instance***
| OS_FLOATING_IP_POOLS | | | Name of the pool of floating ips from which one should be associated with the new instance
| **CI-instance variables**  | | |
| USER | `$USER` | | Name of the user on the ***ci-instance*** that registered the gitlab-runner
| SSH_FILE | `<path-to-ssh-file>` | | Path to ssh file on the ci-instante to connect to the deployment-instance e.g `/home/$USER/.ssh/id_rsa` |
| **Registry variables** | | |
| DOCKER_IO_USER | | | Username for docker.io |
| DOCKER_IO_PASSWORD | | | Password for docker.io |
| REGISTRY_URL | `$CI_REGISTRY_IMAGE` | | Path to the registry used for building
| REGISTRY_TOKEN | | | Token for the registry specified as `REGISTRY_URL`. Actually, this token also requires API access to the project. |
| **Pipeline variables** | | |
| BUILD_ARGUMENTS | `""` | `"--latest", "--vulnerability-scan", ...` | String of arguments that will be appended to `python3 start_build.py` e.g. `BUILD_ARGUMENTS="--latest"` |
| DOCKER_PRUNE | `"false"` | `["true","false"]` | If `"true"` all docker images, containers and volumes are deleted at the beginning of the build-stage. |
| DEPLOY_PLATFORM | `"true"` | `["true","false"]` | If `"true"` include the `deploy` stage in the pipeline |
| EXECUTE_BUILD | `"true"` | `["true","false"]` | If `"true"` include the `build` stage in the pipeline |
| TEST_STAGE | `"true"` | `["true","false"]` | If `"true"` include the `test` stage in the pipeline. Can only be set to `"true"` if  `DEPLOY_PLATFORM="true"` |

## Pipelines

### Scheduled pipelines

* All variables can be set in the UI.
* If a variable is not specifically set the default values from the project will be taken.

### Merge request pipelines

* Merge request pipelines always use the default CI settings specified in the project settings.
* Merge request pipelines always use the ***deployment-instance*** associated with `DEPLOYMENT_INSTANCE_NAME=kaapana_ci_gpu`.

### Web pipelines

* Web pipelines can be started via the UI.
* All variables are configurable.
* If a variable is not specifically set the default values from the project will be taken.

## Artifacts and the build directory

### Build directory

* The kaapana repository is cloned into `CI_BUILD_DIR=/home/$USER/builds/$CI_COMMIT_SHORT_SHA`

### Artifacts and log files

* Artifacts such as log files are stored in `ARTIFACTS_DIR=/home/$USER/artifacts/$CI_COMMIT_SHORT_SHA`.
* When startin a new pipeline on the same commit, all files in this directory and subdirectories are removed.


## Start a pipeline in the web-interface on your own openstack machine

1. Just navigate to https://codebase.helmholtz.cloud/kaapana/kaapana/-/pipelines/new
2. Select the branch you want to be build, deployed and tested
3. Set `DEPLOYMENT_INSTANCE_IP` to the floating ip of your openstack instance
4. Set `DEPLOYMENT_INSTANCE_NAME` to a random name - doesn't really matter.
5. Set `OS_CREATE: false`
6. Click on ***New pipeline***

[Optional]: Finetune your pipeline with the variables: `BUILD_ARGUMENTS`, `DEPLOY_PLATFORM`, `TEST_STAGE`