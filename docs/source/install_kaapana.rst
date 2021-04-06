.. _install_kaapana:

Install Kaapana
===============
This manual is int

Step 1: Server Installation
---------------------------
This part describes the preparation of the host system for Kaapana.
Besides a few required software packages, mainly Microk8s is installed, to setup Kubernetes. 

.. hint::

  | **GPU support -> Currently only Nvidia GPUs are supported!**
  | GPU support requires installation of the `Nvidia drivers <https://www.nvidia.de/Download/index.aspx?lang=en>`_ .
  | For Ubuntu Server 20.04 :code:`sudo apt install nvidia-driver-<version>-server`
  | should also work **BUT** check the hibernation settings afterwards (`see <https://www.unixtutorial.org/disable-sleep-on-ubuntu-server/>`_) 
  | -> :code:`sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`
  | --> reboot required!
  | Please make sure the :code:`nvidia-smi` command is working as expected!

Before the example platform "Kaapana-platform" can be deployed, all dependencies must be installed on the server. 
To do this, you can use the :term:`server-installation-script`, located at :code:`kaapana/server-installation/server_installation.sh`, by following the steps listed below.

1. Copy the script to your target-system (server)
2. Make it executable: :code:`chmod +x server_installation.sh`
3. Execute the script: :code:`sudo ./server_installation.sh`
4. Reboot the system :code:`sudo reboot`
5. (optional) Enable GPU support for Microk8s :code:`sudo ./server_installation.sh -gpu`

Step 2: Platform Deployment
---------------------------
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
         DEV_MODE="false"
         
         REGISTRY_URL="local"
         ...

   .. tab:: Private registry

      .. important:: The beginning slash for <registry-project> is important!

      .. code-block:: python

         ...
         REGISTRY_URL="<registry-url>"
         ...


3. Make it executable with :code:`chmod +x install_platform.sh`
4. Execute the script:

.. tabs::

   .. tab:: Local build

      :code:`./install_platform.sh --chart-path kaapana/build/kaapana-platform-<version>.tgz`

   .. tab:: Private registry

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



