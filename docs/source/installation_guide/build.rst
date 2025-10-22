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
Perform these steps on the build machine. The recommended build system is Ubuntu 24.04 (x64).
Kaapana can only be built and run on x64 systems.
Building on other operating systems or architectures has not been tested and may lead to unexpected issues, for which no official support is provided.

.. important::

  | **Disk space needed:**
  | For the complete build of the project ~90GB (~110GB including build cache) of container images will be stored at :code:`/var/snap/docker/common/var-lib-docker`.
  | When creating offline installation tarball, ~80GB additional disk space is needed.

Before you get started you should be familiar with the basic concepts and components of Kaapana (see :ref:`about_kaapana`).
You should also have the following packages installed on your build-system.

#. Dependencies 

   .. tabs::

      .. tab:: Ubuntu

         | :code:`sudo apt update && sudo apt install -y nano curl git python3 python3-pip`

      .. tab:: AlmaLinux

         | :code:`sudo dnf update && sudo dnf install -y nano curl git python3 python3-pip`


#. Clone the repository:

   | :code:`git clone -b master https://github.com/kaapana/kaapana.git`

#. Python requirements 

   :code:`python3 -m pip install -r kaapana/build-scripts/requirements.txt`

   .. tip::

      | **Use a virtual environment for installing Python dependencies.**
      | This is a recommended best practice.
      |
      | On Ubuntu 24.04 and similar distributions, due to changes in Python packaging (see `PEP 668 <https://peps.python.org/pep-0668/>`_), installing packages with :code:`pip` outside of a virtual environment may result in errors or warnings.
      |
      | To avoid issues, create and activate a virtual environment **before** running the requirements installation:
      
      .. tabs::

         .. tab:: venv

            **Recommended for beginners!**

            **Creation step** (only needed once):

            .. code-block:: bash
            
               # Install the 'venv' package if not already installed
               sudo apt install -y python3-venv
               
               # Create the virtual environment (only needed once)
               python3 -m venv kaapana/.venv

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the virtual environment
               source kaapana/.venv/bin/activate

            Then install the Python requirements.

         .. tab:: pipenv


            **Installation step** (only needed once):

            .. code-block:: bash

               # Install pipenv
               pip install pipenv

               # Create and activate the environment (only needed once)
               pipenv install

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the environment
               pipenv shell

            Then install the Python requirements.

         .. tab:: poetry

            **Installation step** (only needed once):

            .. code-block:: bash

               # Install Poetry
               pip install poetry

               # Create and activate the environment (only needed once)
               poetry install

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the environment
               poetry shell

            Then install the Python requirements.
         
         .. tab:: conda

            | **Licensing Notice**: Anaconda has licensing restrictions for commercial use. For details, refer to the `Anaconda Terms of Service <https://www.anaconda.com/terms-of-service>`_. 
            |
            | Conda can be installed in various ways, and it’s important to research the best option for your needs to ensure compliance with the relevant licensing terms.
            |
            | If you have Conda installed, you can create and activate a Conda environment and then proceed to install the Python requirements.

            **Creation step** (only needed once):

            .. code-block:: bash

               # Create a Conda environment (only needed once)
               conda create -n kaapana python=3.x

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the Conda environment
               conda activate kaapana

            Then install the Python requirements

#. Snap 

   .. tabs::

      .. tab:: Ubuntu

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo apt install -y snapd`
         | A **reboot** is needed afterwards!

      .. tab:: AlmaLinux

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo dnf install -y epel-release && sudo dnf install -y snapd`
         | A **reboot** is needed afterwards!

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
            platform_filter: "kaapana-admin-chart" # platform-chart name (e.g. racoon-admin-chart, kaapana-admin-chart, wdb-chart)
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

         .. note::
            1. If the username and password are not working, you may need to use an **access token** instead.
            2. Ensure that the **username/access token does not contain spaces**.

      .. tab:: Build With Local Registry

         | Not recommended. 
         | If a private registry is not available, it is possible to setup a local registry. 
         | This may be helpful for one-time show-casing, testing, developing, or if there are any issues with connection to the remote registry.
         | This solution is only persistent while the docker container containing the registry is running. It also works only locally and cannot be distributed. 
         | For building with a local registry, you need to set up a local Docker registry with basic authentication with following steps:

         1. Create credentials (replace **<registry user>** and **<registry password>**):

            .. code-block:: bash
            
               mkdir auth
               docker run --entrypoint htpasswd httpd:2.4.58 -Bbn <registry user> <registry password> > auth/htpasswd
            

         2. Start the Docker registry with basic authentication:

            .. code-block:: bash
            
               docker run -d -p 5000:5000 --restart unless-stopped --name registry -v "$(pwd)"/auth:/auth -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd registry:2.8.3
            

         3. Configure ``build_config.yaml``:

            .. code-block:: python
               :emphasize-lines: 2
               
               ...
               default_registry: "localhost:5000"
               ...


      .. tab:: Build Tarball

         | Not recommended.
         | In case platfrom should be deployed in the machine without internet access (i.e. offline), 
         | installation files, containers and helm charts need to be pre-build on the server 
         | with internet access and copied on the server, where requirements can be installed and platfrom deployed. 
         | This configuration creates an image tarball and offline microk8s installer
         
         .. code-block:: python
            :emphasize-lines: 2, 4, 5, 6
               
            ...
            default_registry: "registry.local/offline/offline" # dummy registry user for tagging purposes only
            ...
            build_only: true # charts and containers will only be build and not pushed to the registry
            create_offline_installation: true # Advanced feature - whether to create a docker dump from which the platform can be deployed offline (file-size ~50GB)
            push_to_microk8s: false # Advanced feature - inject container directly into microk8s after build
            ...

         | Installer will be available in ``kaapana/build/microk8s-offline-installer``
         | Tarball will be available in ``kaapana/build/kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar``

#. After the configuration has been adjusted, the build process can be started with:

   | :code:`./kaapana/build-scripts/start_build.py -u <registry user> -p <registry password>`

   This takes usually (depending on your hardware) around 1h.
   
   .. hint::
      **While developing**
      It is possible to set the username/access token and password in the config file instead of passing them as parameters.
      This approach should be used only for development cases, not in production environments.

#. You can find the build-logs and results at :code:`./kaapana/build`

The next step will explain how to install the Kubernetes cluster via the :code:`server_installation.sh` script.
