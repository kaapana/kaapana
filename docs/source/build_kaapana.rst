.. _build_kaapana:

Build Kaapana
=============

Requirements
------------

Before you get started you should be familiar with the basic concepts and components of Kaapana see :ref:`what_is_kaapana`.
You should also have the following packages installed on your build-system.

We expect the sudo systemctl restart snapd

#. Dependencies 

   .. tabs::

      .. tab:: Ubuntu

         | :code:`sudo apt install -y curl git python3 python3-pip`

      .. tab:: Centos

         | :code:`sudo yum install -y curl git python3 python3-pip`

#. Clone the repository:

   | :code:`git clone https://github.com/kaapana/kaapana.git` 
   | (**alternative:** :code:`git clone https://phabricator.mitk.org/source/kaapana.git`)
   | :code:`git checkout master`

#. Python requirements 
   
   :code:`python3 -m pip install -r kaapana/build-scripts/requirements.txt`

#. Snap 

   .. tabs::

      .. tab:: Ubuntu

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo apt install -y snapd`
         | A **reboot** is needed afterwards!

      .. tab:: Centos

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo yum install -y epel-release`
         | :code:`sudo yum update -y`
         | :code:`sudo yum install snapd`
         | :code:`sudo systemctl enable --now snapd.socket`
         | :code:`sudo snap wait system seed.loaded`

#. Docker

   :code:`sudo snap install docker --classic --channel=19.03.13`

#. In order to docker commands as non-root user you need to execute the following steps:

   | :code:`sudo groupadd docker`
   | :code:`sudo usermod -aG docker $USER`
   | For more information visit the `Docker docs <https://docs.docker.com/engine/install/linux-postinstall/>`_ 

#. Helm

   :code:`sudo snap install helm --classic --channel=3.5/stable`

#. Reboot

   :code:`sudo reboot`

#. Test Docker

   | :code:`docker run hello-world`
   | -> this should work now without root privileges

#. Helm plugins

   | :code:`helm plugin install https://github.com/chartmuseum/helm-push`
   | :code:`helm plugin install https://github.com/instrumenta/helm-kubeval`


Creating an example platform
----------------------------
 
The process of creating a Kaapana-based platform involves the following steps that should be executed on a dedicated physical or virtual server:

1. Build and push all :term:`Dockerfiles<docker>`
2. Build and push all :term:`Helm Charts<helm>` (optional - you can use our registry)
3. Install all server requirements with the :term:`server-installation-script`
4. Deploy the platform with the :term:`platform-installation-script`

Build modes
^^^^^^^^^^^
If you **don't** have access to a Docker registry with **already built containers** for Kaapana, you need to build them first.
This is comparable to a binary of regular software projects - if you already have access to it, you can continue with **step 3**.

| The complete build will take **~4h** (depending on the system)! 
| Currently Kaapana supports three different **build-modes**:

#. **Local build**

   | By choosing this option you will need **no external Docker registry** to install the platform.
   | All Docker containers will be build and used locally on the server.
   | The Helm charts will still be downloaded from the DKFZ registry, as long as there is no local solution.
   | **Extensions don't work with this mode yet**

#. **Contaienr registry**

   This option will use a remote container registry.
   Since we're also using charts and other artifacts, the used registry must have `OCI support <https://opencontainers.org/>`__ .
   We recommend `Gitlab <https://gitlab.com/>`__ or `Harbor <https://goharbor.io/>`__ as registry software.
   Unfortunately, Dockerhub does not yet support OCI, and thus cannot currently be used with Kaapana. 
   We recommend `gitlab.com <https://gitlab.com/>`__ as a replacement.

The following sections include a configuration example for each of the options (if applicable).

Steps 1&2: Build Dockerfiles and Helm Charts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Step 1&2 will be handled with a build-script, which you can find within the repository at :code:`kaapana/build-scripts/start_build.py`.

Before you start the build-process, you should have a look at the build-configuration at :code:`kaapana/build-scripts/build-configuration.yaml` and adapt it accordingly to your chosen build configuration as shown below.

.. tabs::

   .. tab:: Local build

      .. code-block:: python
         :emphasize-lines: 2,3,7,8,9,10,11

         http_proxy: ""
         build_mode: "local"
         default_container_registry: "local"
         default_container_project: "" 
         log_level: "WARN"
         build_containers: true
         push_containers: false
         build_charts: true
         push_charts: false
         create_package: true

   .. tab:: Private registry

      | You need to login first: :code:`docker login <registry-url>`.
      | Then you must adjust the configuration as follows:

      .. code-block:: python
         :emphasize-lines: 2,3,4,5,7,8,9,10,11

         http_proxy: ""
         build_mode: "private"
         default_container_registry: "<registry-url>"
         default_container_project: "<registry-project>" 
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
