.. _getting_started:


Getting started
===============

This manual is intended to provide a quick and easy way to get started with :term:`Kaapana<kaapana-platform>`.

:term:`Kaapana<kaapana-platform>` is not a ready-to-use software but a toolkit that enables you to build the platform that fits your specific needs.

The steps described in this guide will build an example :term:`platform`, which is a default configuration and contains many of the typical platform :term:`components<component>`. This basic platform can be used as a starting-point to derive a customized platform for your specific project.

Requirements
------------

Before you get started you should be familiar with the basic concepts and components of Kaapana see :ref:`what_is_kaapana`.
You should also have the following packages installed on your build-system.

We expect the sudo systemctl restart snapd

1. Clone the repository:

   | :code:`git clone https://github.com/kaapana/kaapana.git`
   
   or   
   
   | :code:`git clone https://phabricator.mitk.org/source/kaapana.git`

2. Snap 

   .. tabs::

      .. tab:: Ubuntu

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo apt install snapd`
         | A **reboot** is needed afterwards!

      .. tab:: Centos

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo yum install -y epel-release`
         | :code:`sudo yum update -y`
         | :code:`sudo yum install snapd`
         | :code:`sudo systemctl enable --now snapd.socket`
         | :code:`sudo snap wait system seed.loaded`

3. Python3 

   .. tabs::

      .. tab:: Ubuntu

         | :code:`sudo apt install python3 python3-pip`

      .. tab:: Centos

         | :code:`sudo yum install python3 python3-pip`

4. Python requirements 
   
   :code:`python3 -m pip install -r kaapana/build-scripts/requirements.txt`

5. Docker

   :code:`sudo snap install docker --classic`

6. (optional) Helm

   :code:`sudo snap install helm --classic --channel=3.3/stable`

7. Reboot

   :code:`sudo reboot`

8. (optional) Helm-push plugin

   :code:`helm plugin install https://github.com/chartmuseum/helm-push`

9. (optional) Helm-kubeval plugin

   :code:`helm plugin install https://github.com/instrumenta/helm-kubeval`

.. hint::

  | **Docker as a non-root user**
  | In order to docker commands as non-root user you need to execute the following steps:
  | :code:`sudo groupadd docker`
  | :code:`sudo usermod -aG docker $USER`
  | :code:`sudo reboot` -> to reboot the system
  | :code:`docker run hello-world` -> this should work now without root privileges
  | For more information visit the `Docker docs <https://docs.docker.com/engine/install/linux-postinstall/>`_ 


Creating an example platform
----------------------------
 
The process of creating a Kaapana-based platform involves the following steps that should be executed on a dedicated physical or virtual server:

1. Build and push all :term:`Dockerfiles<docker>`
2. Build and push all :term:`Helm Charts<helm>` (optional - you can use our registry)
3. Install all server requirements with the :term:`server-installation-script`
4. Deploy the platform with the :term:`platform-installation-script`

Build modes
^^^^^^^^^^^
Currently Kaapana supports three different **build-modes**:

1. **Local build (default)**

   By choosing this option you will need **no external Docker registry** to install the platform. All Docker containers and Helm charts will be build and used locally on the server.
   
2. **Dockerhub**

   `Dockerhub <https://hub.docker.com/>`_  offers a **free solution to store Docker containers** in a registry. The disadvantage of this method is that network access to Dockerhub must be guaranteed and all stored containers are publicly accessible (in the free version).

3. **Private registry**

   The third option is to use a private Docker Registry to manage the containers used. This option comes with many **additional features like access controll or the possibility to manage helm charts** directly in the registry. The disadvantage of a private registry is, that you have to either host it yourself or at least pay for it. We recommend `Harbor <https://goharbor.io/>`__ or `Artifactory <https://jfrog.com/artifactory/>`__ as professional solutions for a custom registry.

The following sections include a configuration example for each of the options (if applicable).

Steps 1&2: Build Dockerfiles and Helm Charts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Step 1&2 will be handeled with a build-script, which you can find it within the repository at :code:`kaapana/build-scripts/start_build.py`.

Before you start the build-process, you should have a look at the build-configuration at :code:`kaapana/build-scripts/build-configuration.yaml` and adapt it according as shown below according to you chosen build configuration.

.. tabs::

   .. tab:: Local build

      .. code-block:: python
         :emphasize-lines: 2,3,7,8,9,10,11

         http_proxy: ""
         build_mode: "local"
         default_container_registry: "local"
         default_container_project: "" 
         default_chart_registry: "https://dktk-jip-registry.dkfz.de/chartrepo/"
         default_chart_project: "kaapana-public"
         log_level: "WARN"
         build_containers: true
         push_containers: false
         build_charts: true
         push_charts: false
         create_package: true

   .. tab:: Dockerhub

      | Use Dockerhub as the target registry (username johndoe):
      | You need to login into Dockerhub: :code:`docker login`.
      | Then you must adjust the configuration as follows:

      .. code-block:: python
         :emphasize-lines: 2,3,7,8,9,10,11

         http_proxy: ""
         build_mode: "dockerhub"
         default_container_registry: "johndoe"
         default_container_project: "" 
         default_chart_registry: "https://dktk-jip-registry.dkfz.de/chartrepo/"
         default_chart_project: "kaapana-public"
         log_level: "WARN"
         build_containers: true
         push_containers: true
         build_charts: false
         push_charts: false
         create_package: false

   .. tab:: Private registry

      | You need to login first: :code:`docker login <registry-url>`.
      | Then you must adjust the configuration as follows:

      .. code-block:: python
         :emphasize-lines: 2,3,4,5,7,8,9,10,11

         http_proxy: ""
         build_mode: "private"
         default_container_registry: "<registry-url>"
         default_container_project: "<registry-project>" 
         default_chart_registry: "<registry-chart-repo-url>"
         default_chart_project: "<registry-chart-project>"
         log_level: "WARN"
         build_containers: true
         push_containers: true
         build_charts: true
         push_charts: true
         create_package: false

We will utilize the DKFZ registry for Helm chart as long as there is no other easy alternative.

.. important::

  | **Disk space needed:**
  | For the complete build of the project ~50GB of container images will be stored at :code:`/var/snap/docker/common/var-lib-docker`.
  | If you use build-mode local it will be ~120GB since each container will be also imported separately into containerd.
  | In the future we will also provide an option to delete the docker image after the import.


Start the build process:
:code:`python3 kaapana/build-scripts/start_build.py`

Step 3: Server Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. hint::

  | **GPU support -> Currently only Nvidia GPUs are supported!**
  | GPU support requires installation of the `Nvidia drivers <https://www.nvidia.de/Download/index.aspx?lang=en>`_ .
  | For Ubuntu Server 20.04 :code:`sudo apt install nvidia-driver-<version>-server`
  | should also work **BUT** check the hibernation settings afterwards --> `see <https://www.unixtutorial.org/disable-sleep-on-ubuntu-server/>`_
  | -> reboot required!
  | Please make sure the :code:`nvidia-smi` command is working as expected!

Before the example platform "Kaapana-platform" can be deployed, all dependencies must be installed on the server. 
To do this, you can use the :term:`server-installation-script`, located at :code:`kaapana/server-installation/server_installation.sh`, by following the steps listed below.

1. Copy the script to your target-system (server)
2. Make it executable: :code:`chmod +x server_installation.sh`
3. Execute the script: :code:`sudo ./server_installation.sh`
4. Reboot the system :code:`sudo reboot`
5. (optional) Enable GPU support for Microk8s :code:`sudo ./server_installation.sh -gpu`

Step 4: Platform Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The platform is deployed using the :term:`platform-installation-script`, which you can find at :code:`kaapana/platforms/kaapana-platform/platform_installation/install_platform.sh`.

Copy the script to your target-system (server) and **adjust it as described below**:

1. Open the :code:`install_platform.sh` script on the server
   
   :code:`nano install_platform.sh`

2. Have a look at the variables on top of the script.
   
   **You need to do at least the following customizations:**

.. tabs::

   .. tab:: Local build

      .. code-block:: python

         ...
         CONTAINER_REGISTRY_URL="local"
         CONTAINER_REGISTRY_PROJECT=""
         ...
         DEV_MODE="false"
         ...

   .. tab:: Dockerhub

      .. code-block:: python

         ...
         CONTAINER_REGISTRY_URL="johndoe"
         CONTAINER_REGISTRY_PROJECT=""
         ...

   .. tab:: Private registry

      .. important:: The beginning slash for <registry-project> is important!

      .. code-block:: python

         ...
         CONTAINER_REGISTRY_URL="<registry-url>"
         CONTAINER_REGISTRY_PROJECT="/<registry-project>"

         CHART_REGISTRY_URL="<registry-chart-url>"
         CHART_REGISTRY_PROJECT="<registry-chart-project>"
         ...


3. Make it executable with :code:`chmod +x install_platform.sh`
4. Execute the script:

.. tabs::

   .. tab:: Local build

      :code:`./install_platform.sh --chart-path kaapana/build/kaapana-platform-<version>.tgz`

   .. tab:: Dockerhub & Private registry

      :code:`./install_platform.sh`

You may be asked the following questions:

1. *Please enter the credentials for the Container-Registry:*

   Use the same credentials you used before with *docker login*

2. *Enable GPU support?*

   Answer *yes* if you have a Nvidia GPU, installed drivers and enabled GPU for Microk8s.

3. *Please enter the domain (FQDN) of the server.*

   You should enter the **domain, hostname or IP-address** where the server is accessible from client workstations.
   **Keep in mind, that valid SSL-certificates are only working with FQDN domains.**

4. *Which <platform-name> version do you want to install?:*

   Specify the version you want to install.

The script will stop and **wait** until the platform is deployed.
Since all Docker containers must be downloaded, this may take some time (~15 min).

After a successful installation you'll get the following message:

.. code-block:: python

   Installation finished.
   Please wait till all components have been downloaded and started.
   You can check the progress with:
   watch microk8s.kubectl get pods --all-namespaces
   When all pod are in the "running" or "completed" state,
   you can visit: <domain>
   You should be welcomed by the login page.
   Initial credentials:
   username: kaapana
   password: kaapana
