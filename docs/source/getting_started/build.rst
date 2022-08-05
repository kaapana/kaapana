.. _build:

Build Kaapana
*************

It is important to note that the building of Kaapana (including the cloning of the repository etc.) is completely separated from the actual installation / deployment of the platform.
Building the repository, which is described in this chapter, refers to the creation of the required containers and Helm Charts needed for an installation.
The results of this build (containers and charts) are usually pushed into a registry and downloaded from there for the installation on the actual deployment server (where the platform will be running).

.. important::

  | **1) Do you really need to build the project?**
  | Only build the project if you don't have access to an existing registry containing the Kaapana binaries or if you want to setup your own infrastructure. (Evaluation registry access can be requested from the DKFZ Kaapana Team)
  | 
  | **2) You don't need to build the repository on the deployment server!**
  | A typical misconception we often hear is that you need to clone the repository on the deployment server and build it there. That is not the case! The repository can be built on a completely different machine and the results then made available via a registry. Practically, it is even recommended to separate the repository and the deployment server. Of course it is possible to build the repository on the deployment server (and there is also the possibility to work completely without a registry) - but this should be done in rather rare cases. 
  | 

Build Requirements
------------------
Perform these steps on the build-machine! Recommended operating system is Ubuntu 20.04.

.. important::

  | **Disk space needed:**
  | For the complete build of the project ~60GB of container images will be stored at :code:`/var/snap/docker/common/var-lib-docker`.
  | 50GB will be needed additionally if you enable the generation of an offline-installation-tarball (build-config: create_offline_installation).
  |

Before you get started you should be familiar with the basic concepts and components of Kaapana see :ref:`about_kaapana`.
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

   :code:`sudo snap install helm --classic --channel=3.7/stable`

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

#. Adjust the configuration to your needs: see :ref:`build_config`

#. After the configuration has been adjusted, the build process can be started with:

   | :code:`./kaapana/build-scripts/start_build.py -u <registry user> -p <registry password>`

   This takes usually (depending on your hardware) around 1h.

#. You can find the build-logs and results at :code:`./kaapana/build`

#. If everything has worked, you can proceed with the installation of the deployment server: :ref:`deployment`.
