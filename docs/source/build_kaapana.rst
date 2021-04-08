.. _build_kaapana:

Build Kaapana
=============

Build Requirements
------------------

.. important::

  | **Disk space needed:**
  | For the complete build of the project ~50GB of container images will be stored at :code:`/var/snap/docker/common/var-lib-docker`.
  | If you use build-mode local it will be ~120GB since each container will be also imported separately into containerd.
  | In the future we will also provide an option to delete the docker image after the import.

Before you get started you should be familiar with the basic concepts and components of Kaapana see :ref:`what_is_kaapana`.
You should also have the following packages installed on your build-system.

We expect the sudo systemctl restart snapd

#. Dependencies 

   .. tabs::

      .. tab:: Ubuntu

         | :code:`sudo apt update && sudo apt install -y curl git python3 python3-pip`

      .. tab:: Centos

         | :code:`sudo yum install -y curl git python3 python3-pip`

#. Clone the repository:

   | :code:`git clone https://github.com/kaapana/kaapana.git` 

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

   :code:`sudo snap install docker --classic --channel=latest/stable`

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


Building the example platform
------------------------------
 
The process of creating a Kaapana-based platform involves the following steps that should be executed on a dedicated machine:

#. Build all :term:`Dockerfiles<docker>` and :term:`Helm Charts<helm>` from the repository
#. (optional) Push them to an external container regisry
#. Install all server requirements with the :term:`server-installation-script`
#. Deploy the platform with the :term:`platform-installation-script`

Build modes
-----------

If you **don't** have access to a container registry with **already built containers** for Kaapana, you need to build them first.
This is comparable to a binary of regular software projects - if you already have access to it, you can continue with **step 3**.

| The complete build will take **~1h** (depending on the system)! 
| Currently Kaapana supports two different **build-modes**:

#. **Local build**

   | By choosing this option you will need **no external container registry** to install the platform.
   | All containers will be build and used locally on the server.

#. **Container registry**

   | This option will use a remote container registry.
   | Since we're also using charts and other artifacts, the registry must have `OCI support <https://opencontainers.org/>`__ .
   | We recommend `Gitlab <https://gitlab.com/>`__ or `Harbor <https://goharbor.io/>`__ as registry software.
   | Unfortunately, Dockerhub does not yet support OCI, and thus cannot currently be used with Kaapana. We recommend `gitlab.com <https://gitlab.com/>`__ as a replacement.

The following sections include a configuration example for each of the options (if applicable).

Steps 1&2: Build Dockerfiles and Helm Charts
--------------------------------------------

Step 1&2 will be handled with a build-script, which you can find within the repository at :code:`kaapana/build-scripts/start_build.py`.

Before you start the build-process, you should have a look at the build-configuration at :code:`kaapana/build-scripts/build-configuration.yaml` and adapt it accordingly to your chosen build configuration as shown below.

.. tabs::

   .. tab:: Local build

      .. code-block:: python
         :emphasize-lines: 2,3,4,5,6,7,8,9,10,11

         http_proxy: ""
         default_container_registry: ""
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
         :emphasize-lines: 2,3,4,5,6,7,8,9,10,11

         http_proxy: ""
         default_container_registry: "<registry-url>" (e.g. registry.gitlab.com/<user>/<project> .)
         log_level: "WARN"
         build_containers: true
         push_containers: true
         build_charts: true
         push_charts: true
         create_package: false



Adjust build-configuration:

| :code:`nano kaapana/build-scripts/build-configuration.yaml`

Start the build process:

| :code:`python3 kaapana/build-scripts/start_build.py`
