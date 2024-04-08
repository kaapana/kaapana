.. _kaapana_offline:

Advanced: How to prebuild & deploy Kaapana offline
***************************************************

While it is generally not recommended, it is indeed possible to build and deploy Kaapana offline. This process involves several steps to ensure that all necessary components are available for deployment on a server without internet access.

Additional requirements:
^^^^^^^^^^^^^^^^^^^^^^^^

- ~75GB additional disk space used by offline installation tarball
- Prebuild tarball: kaapana-admin-chart-<version>-images.tar
- Prebuild offline microk8s installer

Prebuild tarball & offline microk8s installer:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Configure Build Settings
   
   Modify the build configurations in ``kaapana/build-scripts/build-config.yaml`` to update the following settings:

   .. code-block:: python

      default_registry: "<registry-url-you-got-from-developer>" # e.g. "registry.local/offline/offline"
      build_only: true # charts and containers will only be build and not pushed to the registry
      create_offline_installation: true # Advanced feature - whether to create a docker dump from which the platform can be deployed offline (file-size -50GB)
      push_to_microk8s: false # Advanced feature - inject container directly into microk8s after build


2. Prebuild
   
   Run the build script to prebuild microk8s installer and Kaapana tarball:

   .. code-block:: bash

      $ ./kaapana/build-scripts/start_build.py

3. Installer will be available in `kaapana/build/microk8s-offline-installer`
4. Tarball will be available in `kaapana/build/kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar`

Server installation:
^^^^^^^^^^^^^^^^^^^^

.. note::
   Before running server installation script, assure yourself, that you have `kaapana/build/microk8s_offline_installer` in the build directory.
   That can be created by running prebuild and copying it into the offline server, as described in the previous section.

Install Microk8s Offline

   Navigate to the microk8s offline installer directory:

   .. code-block:: bash

      $ cd kaapana/build/microk8s-offline-installer

   Execute the server installation script with the ``--offline`` flag:

   .. code-block:: bash

      $ sudo ./server_installation.sh --offline


Offline deploy:
^^^^^^^^^^^^^^^

1. Import Images into Microk8s Registry
   
   Go to the build directory:

   .. code-block:: bash

      $ cd kaapana/build/

   Run the deployment script to import images into the microk8s registry:

   .. code-block:: bash

      $ ./kaapana-admin-chart/deploy_platform.sh --import-images-tar kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar

2. Modify Deployment Script
   
   Edit the ``deploy_platform.sh``:
   
   .. code-block:: python
      
      CONTAINER_REGISTRY_URL="<registry-url-you-got-from-developer>"

3. Start Offline Installation

   Execute the deployment script with the necessary parameters. 

   .. code-block:: bash

      $ ./kaapana-admin-chart/deploy_platform.sh --chart-path kaapana-admin-chart/kaapana-admin-chart-<version>.tgz

   By specifying --chart-path argument, offline mode is automatically set to true. 



