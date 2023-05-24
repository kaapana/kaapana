.. _deployment:

Platform Deployment
*******************

Deployment Requirements
-----------------------

#. **Host system**

   | You will need some kind of :term:`server` to run the platform on.
   | Minimum specs:

   - OS: Ubuntu 20.04/22.04 or Ubuntu Server 20.04/22.04
   - CPU: 8 cores (recommended 16+)
   - RAM: 64GB+ (recommended 128GB+) 
   - Storage for application-data (fast-dir): 100GB (recommended >200GB) 
   - Storage for imaging-data (slow-dir): depends on your needs 


#. **Access to a docker registry or a tarball with built docker containers**

   Before proceeding with further installation steps, make sure you have access to a docker registry or a tarball with built Kaapana docker containers, otherwise please visit :ref:`getting_started`.

   .. hint::

      | **Accessing Docker Registry or Tarball with Pre-built Docker Containers**
      | If you are interested in exploring our platform, we encourage you to get in touch with us (:ref:`contact`). Should you choose to do so, we will gladly offer you two options for accessing it. You can either receive credentials for our docker registry or receive a tarball that includes the necessary docker containers. With these options, you can directly deploy the platform without the need to go through the building process.

   To provide the services in Kaapana, the corresponding containers are needed.
   These can be looked at as normal binaries of Kaapana and therefore only need to be built if you do not have access to already built containers via a container registry or a tarball.

   .. .. mermaid::

   ..    flowchart TB
   ..       a1(Do you want to use a remote container registry or a tarball for your Kaapana installation?)
   ..       a1-->|Yes| a2(Do you already have access to a registry or a tarball containing all needed containers?)
   ..       a1-->|No| b1
   ..       a2-->|Yes| c1
   ..       a2-->|No| b1
   ..       b1(Build Kaapana) --> c1
   ..       c1(Install Kaapana)


#. **Known Server Configuration**

   The **domain, hostname or IP-address** has to be known and correctly configured for the system. 
   **Proxy**, **DNS**, **TLS/SSL Certificates** etc. should be already configured (see :ref:`server_config`). 

   
Installation of Server Dependencies 
-----------------------------------

This part describes the preparation of the host system for Kaapana.
Besides a few required software packages, mainly Microk8s is installed, to setup Kubernetes. 

.. hint::

  | **GPU support (Nvidia GPUs)**
  | GPU support requires the installation of Nvidia drivers.
  | Please make sure the :code:`nvidia-smi` command is working as expected!

Before the example platform "Kaapana-platform" can be deployed, all dependencies must be installed on the server. 
To do this, you can use the :term:`server-deployment-script`, located at :code:`kaapana/server-installation/server_installation.sh`, by following the steps listed below.

1. Copy the script to your target-system (server)
2. Make it executable:

   | :code:`chmod +x server_installation.sh`

3. Execute the script:

   | :code:`sudo ./server_installation.sh`

4. Reboot the system 

   | :code:`sudo reboot`

5. (optional) Enable GPU support for Microk8s 

   | :code:`sudo ./server_installation.sh -gpu`

.. hint::

  | **Server Dependency Uninstallation**
  | To uninstall the server-packages, you can use :code:`sudo ./server_installation.sh --uninstall`


Platform Deployment
-------------------

.. hint::

  | **Filesystem directories**
  | In the default configuration there are two locations on the filesystem, which will be used for stateful data on the host machine:
  | 1. ``fast_data_dir=/home/kaapana``: Location of data that do not take a lot of space and should be loaded fast. Preferably, a SSD is mounted here.
  | 2. ``slow_data_dir=/home/kaapana``:  Location of huge files, like images or our object store is located here.  Preferably, a HDD is mounted here.
  | They can be adjusted in the :term:`platform-deployment-script` and can also be identical (everything is stored at one place).

The platform is deployed using the :term:`platform-deployment-script`, which you can find at :code:`kaapana/build/kaapana-admin-chart/deploy_platform.sh`.

Copy the script to your target-system (server) and **adjust it as described below**:

1. Open the :code:`deploy_platform.sh` script on the server
   
   :code:`nano deploy_platform.sh`

2. Have a look at the variables on top of the script.
   
**You need to do at least the following customizations:**
Note: If you have already built the platform, these variables should have been filled in.

.. tabs::

   .. tab:: Private registry

      .. code-block:: python

         ...
         CONTAINER_REGISTRY_URL="<registry-url>"
         ...

   .. tab:: Tarball

      .. code-block:: python

         ...
         CONTAINER_REGISTRY_URL="<registry-url-you-got-from-developer>"
         ...

3. Make it executable with :code:`chmod +x deploy_platform.sh`
4. Execute the script:

.. note:: 

   If you are use a tarball make sure that you also make the following changes to the :code:`deploy_platform.sh` file:

   .. code-block:: python

      ...
      OFFLINE_MODE="true"
      DEV_MODE="false"
      CONTAINER_REGISTRY_URL="<registry-url-you-got-from-developer>"
      ...

.. tabs::

   .. tab:: Private registry

      :code:`./deploy_platform.sh`

   .. tab:: Tarball

      :code:`./deploy_platform.sh --upload-tar <path-to-tarball-file>`

You may be asked the following questions:

1. *server domain (FQDN):*

   You should enter the **domain, hostname or IP-address** where the server is accessible from client workstations.
   **Keep in mind, that valid SSL-certificates are only working with FQDN domains.**

2. *Enable GPU support?*

   Answer *yes* if you have a Nvidia GPU, installed drivers and enabled GPU for Microk8s.

3. *Please enter the credentials for the Container-Registry:*

   Use the credentials to your own registry or the ones provided to you by the Kaapana team.

The script will stop and **wait** until the platform is deployed.
Since all Docker containers must be downloaded, this may take some time (~15 min).

After a successful deployment you'll get the following message:

.. code-block:: python

   Deployment done.
   Please wait till all components have been downloaded and started.
   You can check the progress with:
   watch microk8s.kubectl get pods --all-namespaces
   When all pod are in the "running" or "completed" state,
   you can visit: <domain>
   You should be welcomed by the login page.
   Initial credentials:
   username: kaapana
   password: kaapana


Undeploy Platform
^^^^^^^^^^^^^^^^^

To undeploy the Kaapana platform, the kaapana-platform-chart and all related charts need to be deleted. For that, run the deployment script :code:`./deploy_platform.sh` and choose the **2) Undeploy** option.

If the **undeployment fails**, make sure to manually check that

1. All helm charts are deleted. All helm charts in Kaapana are created with the same namespace so that they are distinguished from possible other charts

   :code:`helm ls -n kaapana`

2. All pods are deleted. Kaapana uses multiple namespaces for managing deployment and pods, i.e. **kaapana, flow-jobs flow, monitoring, store, meta, base**

   :code:`kubectl get pods -A`

.. hint::

   | The :code:`./deploy_platform.sh` script also has a purge flag.
   | :code:`--purge-kube-and-helm` will purge all kubernetes deployments and jobs as well as all helm charts. Use this if the undeployment fails or runs forerver.
