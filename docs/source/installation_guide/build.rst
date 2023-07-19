.. _build:

Build Kaapana
*************

It is important to note that the building of Kaapana (including the cloning of the repository etc.) is completely separated from the actual installation / deployment of the platform.
Building the repository, which is described in this chapter, refers to the creation of the required containers and Helm Charts needed for an installation.
The results of this build (containers and charts) are usually pushed into a registry and downloaded from there for the installation on the actual deployment server (where the platform will be running).

.. important::

  | **1) Do you really need to build the project?**
  | Only build the project if you don't have access to an existing registry containing the Kaapana binaries or if you want to setup your own infrastructure. Registry access can be requested from the DKFZ Kaapana Team via `Slack <https://kaapana.slack.com/archives/C018MPL9404>`_.
  | 
  | **2) You don't need to build the repository on the deployment server!**
  | A typical misconception we often hear is that you need to clone the repository on the deployment server and build it there. That is not the case! The repository can be built on a completely different machine and the results then made available via a registry. Practically, it is even recommended to separate the repository and the deployment server. Of course it is possible to build the repository on the deployment server (and there is also the possibility to work completely without a registry) - but this should be done in rather rare cases. 
  | 

Build Requirements
------------------
Perform these steps on the build-machine! Recommended operating system is Ubuntu 20.04.

.. important::

  | **Disk space needed:**
  | For the complete build of the project ~90GB (~110GB including build cache) of container images will be stored at :code:`/var/snap/docker/common/var-lib-docker`.
  | 75GB will be needed additionally if you enable the generation of an offline-installation-tarball (build-config: create_offline_installation).
  |

Before you get started you should be familiar with the basic concepts and components of Kaapana (see :ref:`about_kaapana`).
You should also have the following packages installed on your build-system.

#. Dependencies 

   .. tabs::

      .. tab:: Ubuntu

         | :code:`sudo apt update && sudo apt install -y nano curl git python3 python3-pip`

      .. tab:: AlmaLinux

         | TBD

#. Clone the repository:

   | :code:`git clone -b master https://github.com/kaapana/kaapana.git` 

#. Python requirements 
   
   :code:`python3 -m pip install -r kaapana/build-scripts/requirements.txt`

#. Snap 

   .. tabs::

      .. tab:: Ubuntu

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo apt install -y snapd`
         | A **reboot** is needed afterwards!

      .. tab:: AlmaLinux

         | TBD

#. Docker

   :code:`sudo snap install docker --classic --channel=latest/stable`

#. In order to execute docker commands as non-root user you need to execute the following steps:

   | :code:`sudo groupadd docker`
   | :code:`sudo usermod -aG docker $USER`
   | For more information visit the `Docker docs <https://docs.docker.com/engine/install/linux-postinstall/>`_ 

#. Helm

   :code:`sudo snap install helm --classic --channel=latest/stable`

#. Reboot

   :code:`sudo reboot`

#. Test Docker

   | :code:`docker run hello-world`
   | -> this should work now without root privileges

#. Helm plugin

   | :code:`helm plugin install https://github.com/instrumenta/helm-kubeval`


Start Build
------------

#. Generate default build-config

   :code:`./kaapana/build-scripts/start_build.py`

#. Open the build-configuration file

   :code:`nano kaapana/build-scripts/build-config.yaml`

#. Adjust the configuration to your needs:

   .. tabs::

      .. tab:: Build With Remote Registry
         
         We recommend building the project using a registry. If you do not have access to an established registry, we recommend using `Gitlab <https://gitlab.com>`_, which provides a cost-free option to use a private container registry.
         
         .. code-block:: python
            :emphasize-lines: 2

            http_proxy: "" # put the proxy here if needed
            default_registry: "registry.<gitlab-url>/<group-or-user>/<project>" # registry url incl. project Gitlab template: "registry.<gitlab-url>/<group/user>/<project>"
            registry_username: "" # container registry username
            registry_password: "" # container registry password
            container_engine: "docker" # docker or podman
            enable_build_kit: true # Should be false for now: Docker BuildKit: https://docs.docker.com/develop/develop-images/build_enhancements/ 
            log_level: "INFO" # DEBUG, INFO, WARNING or ERROR
            build_only: false # charts and containers will only be build and not pushed to the registry
            create_offline_installation: false # Advanced feature - whether to create a docker dump from which the platform can be deployed offline (file-size ~50GB)
            push_to_microk8s: false # Advanced feature - inject container directly into microk8s after build
            exit_on_error: true  # stop immediately if an issue occurs
            enable_linting: true # should be true - checks deployment validity
            skip_push_no_changes: false # Advanced feature - should be false usually
            platform_filter: "kaapana-admin-chart" # comma seperated platform-chart-names
            external_source_dirs: "" # comma seperated paths
            build_ignore_patterns: "" # comma seperated list of directory paths or files that should be ignored
            parallel_processes: 2 # parallel process count for container build + push 
            include_credentials: false # Whether to include the used registry credentials into the deploy-platform script
            enable_image_stats: false # Whether to enable container image size statistics (build/image_stats.json)
            vulnerability_scan: false # Whether containers should be checked for vulnerabilities during build.
            vulnerability_severity_level: "CRITICAL,HIGH" # Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN. All -> ""
            configuration_check: false # Wheter the Charts, deployments, dockerfiles etc. should be checked for configuration errors.
            configuration_check_severity_level: "CRITICAL,HIGH" # Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN. All -> ""
            create_sboms: false # Create Software Bill of Materials (SBOMs) for the built containers.

      .. tab:: Build Without Remote Registry (Local Only)

         Not recommended!

         .. code-block:: python
            :emphasize-lines: 2,8,9

            http_proxy: "" # put the proxy here if needed
            default_registry: "registry.<gitlab-url>/<group-or-user>/<project>" # registry url incl. project Gitlab template: "registry.<gitlab-url>/<group/user>/<project>"
            registry_username: "" # container registry username
            registry_password: "" # container registry password
            container_engine: "docker" # docker or podman
            enable_build_kit: true # Should be false for now: Docker BuildKit: https://docs.docker.com/develop/develop-images/build_enhancements/ 
            log_level: "INFO" # DEBUG, INFO, WARNING or ERROR
            build_only: true # charts and containers will only be build and not pushed to the registry
            create_offline_installation: true # Advanced feature - whether to create a docker dump from which the platform can be deployed offline (file-size ~50GB)
            push_to_microk8s: false # Advanced feature - inject container directly into microk8s after build
            exit_on_error: true  # stop immediately if an issue occurs
            enable_linting: true # should be true - checks deployment validity
            skip_push_no_changes: false # Advanced feature - should be false usually
            platform_filter: "kaapana-admin-chart" # comma seperated platform-chart-names
            external_source_dirs: "" # comma seperated paths
            build_ignore_patterns: "" # comma seperated list of directory paths or files that should be ignored
            parallel_processes: 2 # parallel process count for container build + push 
            include_credentials: false # Whether to include the used registry credentials into the deploy-platform script
            enable_image_stats: false # Whether to enable container image size statistics (build/image_stats.json)
            vulnerability_scan: false # Whether containers should be checked for vulnerabilities during build.
            vulnerability_severity_level: "CRITICAL,HIGH" # Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN. All -> ""
            configuration_check: false # Wheter the Charts, deployments, dockerfiles etc. should be checked for configuration errors.
            configuration_check_severity_level: "CRITICAL,HIGH" # Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN. All -> ""
            create_sboms: false # Create Software Bill of Materials (SBOMs) for the built containers.



#. After the configuration has been adjusted, the build process can be started with:

   | :code:`./kaapana/build-scripts/start_build.py -u <registry user> -p <registry password>`

   This takes usually (depending on your hardware) around 1h.

#. You can find the build-logs and results at :code:`./kaapana/build`

#. If everything has worked, you can proceed with the installation of the deployment server: :ref:`deployment`.
