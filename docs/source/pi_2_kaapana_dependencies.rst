.. _kaapana_dependencies_doc:

Server Requirements Installation
====================================

This document describes the setup of a system for the **DKTK Kaapana**.

| It is assumed that an independent system is used for the platform.

Requirements
------------
The following requirements should be met:

- Proxy configured (If necessary :ref:`proxy_conf_doc`)
- Internet access
- Root privileges

Intro
-----

All dependencies will be installed by the script `server_installation.sh <https://jip.dktk.dkfz.de/42fef1/server_installation.sh>`_ that you can download from our website.

| The following steps will be executed in the script:

- **Iptables will be reconfigured**
- Kernel will be updated to v4.19
- Swap will be turned off (required by Kubernetes)
- Selinux will be set to permissive (required by Docker)
- Docker-CE will be installed (v18.06.1)
- All Kubernetes tools will be installed (v.1.12)
- Kubernetes will be initialized

If GPU support is desired (recommended):

- NVIDIA drivers will be installed
- Nvidia-Docker2 will be installed


You can find the port configuration in :ref:`specs_doc`

Download the script from the Kaapana Homepage
---------------------------------------------

- Login as root on the server (ssh, ILO or directly)
- Execute the following commands:

::

    curl -L -O https://jip.dktk.dkfz.de/42fef1/server_installation.sh

You should now find the script in your current path.

**Important**: It is recommended to have a look into the script before starting with the installation.

Start the installation process
------------------------------

Make the script executable

::

    chmod +x server_installation.sh

Execute the script

::

    ./server_installation.sh --mode install

The execution of the script should be self-explanatory. You will be
asked a couple of questions during the process.

**GPU support:** 

Right now only NVIDIA GPUs are supported. If you have
such a card in your system you should enable the support.
The "default" Kaapana-Server has two NVIDIA TITAN Xp GPUs.

| If everything runs as expected, the Nvidia card will be detected automatically.
  In this case, it will also be activated automatically.

**IP address and domain check:**

During the process you will be asked to verify the detected IP address and domain.
Please double check them. They are important for the Kubernetes certificate creation.

| **Meanwhile:** 

If the Kernel has to be updated (this will probably be the case), the system will automatically reboot once.
This is expected and the script will continue after the reboot when you login again.

The requirements installation will take ~30 min.

| **Helm installation:** 

If everything went as expected, you will be presented with a success message and the steps to continue.
To deploy Kaapana, `Helm <https://helm.sh/>`_ has to be installed.
Helm is a package management system for Kubernetes. We will install and update the platform via this system.

| Install Helm with:

::

    ./server_installation.sh --mode install-helm

| **End of the script:** 

You should now do a reboot of the system and continue with the platform deployment on the next page :ref:`platform_deployment_doc`.


