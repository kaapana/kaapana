.. _kaapana_offline:

Advanced: How to prebuild & deploy Kaapana offline
*************************************************

While it is generally not recommended, it is indeed possible to build and deploy Kaapana offline. This process involves several steps to ensure that all necessary components are available for deployment on a server without internet access.

Additional requirements:
^^^^^^^^^^^^^^^^^^^^^^^^

- ~75GB additional disk space used by offline installation tarball
- Prebuild tarball: kaapana-admin-chart-<version>-images.tar
- Prebuild offline microk8s installer

Prebuild tarball & offline microk8s installer:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Configure Build Settings
   
   Modify the build configurations in ``/build-scripts/build-config.yaml`` to update the following settings:

   .. code-block:: python

      default_registry: "<registry-url-you-got-from-developer>"
      build_only: true # charts and containers will only be build and not pushed to the registry
      create_offline_installation: true # Advanced feature - whether to create a docker dump from which the platform can be deployed offline (file-size -50GB)
      push_to_microk8s: false # Advanced feature - inject container directly into microk8s after build


2. Prebuild Kaapana
   
   Run the build script to compile and build Kaapana:

   .. code-block:: bash

      $ ./kaapana/build-scripts/start_build.py

3. Installer will be available in `kaapana/build/microk8s-offline-installer`
4. Tarball will be available in `kaapana/build/kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar`
5. Copy from online server to the offline server in the respective folders, before proceeding to the deployment.


Server installation:
^^^^^^^^^^^^^^^^^^^^

.. note::
   Before proceesing with the server installation, assure yourself, that you have `microk8s_offline_installer` directory.
   That can be created by running prebuild and copying it into the offline server, described in the previous section. 

Install Microk8s Offline

   Navigate to the microk8s offline installer directory:

   .. code-block:: bash

      $ cd /kaapana/build/microk8s-offline-installer

   Execute the server installation script with the ``--offline`` flag:

   .. code-block:: bash

      $ sudo ./server_installation.sh --offline


Offline deploy: 
^^^^^^^^^^^^^^^

1. Import Images into Microk8s Registry
   
   Go to the build directory:

   .. code-block:: bash

      $ cd /kaapana/build/

   Run the deployment script to import images into the microk8s registry:

   .. code-block:: bash

      $ ./kaapana-admin-chart/deploy_platform.sh --import-images-tar kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar

2. Modify Deployment Script
   
   Edit the ``deploy_platform.sh`` script:

   .. code-block:: python
      
      CONTAINER_REGISTRY_URL="<registry-url-you-got-from-developer>"
      OFFLINE_MODE=true


3. GPU (Optional) 
   
   If using GPU, move the `microk8s-offline-installer/offline_enable_gpu.py` into `kaapana-admin-chart` directory, so deploy script can access it.

4. Start Offline Installation

   Execute the deployment script with the necessary parameters:

   .. code-block:: bash

      $ ./kaapana-admin-chart/deploy_platform.sh --chart-path kaapana-admin-chart/kaapana-admin-chart-0.3.0-rc1-5-gb082d0c9.tgz --domain 10.128.130.164 --quiet




