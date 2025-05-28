.. _deployment:

Platform Deployment
*******************


Deploy Platform
^^^^^^^^^^^^^^^^

.. hint::

  | **Filesystem directories**
  | In the default configuration there are two locations on the filesystem, which will be used for stateful data on the host machine:
  | 1. ``fast_data_dir=/home/kaapana``: Location of data that do not take a lot of space and should be loaded fast. Preferably, a SSD is mounted here.
  | 2. ``slow_data_dir=/home/kaapana``:  Location of huge files, like images or our object store is located here.  Preferably, a HDD is mounted here.
  | They can be adjusted in the script :code:`deploy_platform.sh` and can also be identical (everything is stored at one place).

The platform is deployed using the script :code:`deploy_platform.sh`, which is created during the build-process at :code:`kaapana/build/kaapana-admin-chart/deploy_platform.sh`.

#. Copy the script to your target-system (server)

#. Adjust the variables in the script to your needs. You find descriptions of all available variables :ref:`below<platform_config>`. You can use your favorite text editor, e.g. :code:`nano`:
   
   :code:`nano deploy_platform.sh`
   
   .. note::

      If you are not using a tarball to deploy the platform, make sure that at least the variable :code:`CONTAINER_REGISTRY_URL` is set to the URL of your container registry.


#. Make the script executable

   :code:`sudo chmod +x deploy_platform.sh`

#. Execute the script:

   .. tabs::

      .. tab:: Private registry

         :code:`./deploy_platform.sh`

      .. tab:: Tarball

         #. Copy the files generated during the :ref:`build process<build>` to your target-system (server), i.e.
         
            - Tarball with all images at ``/kaapana/build/kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar``
            - Helm chart file at ``/kaapana/build/kaapana-admin-chart/kaapana-admin-chart-<version>.tgz``
         
         #. Run the deployment script to import images into the microk8s registry:
            
            .. code-block:: bash
            
               ./deploy_platform.sh --import-images-tar kaapana-admin-chart-<version>-images.tar


         #. Run the deployment script with the offline flag and chart:

            .. code-block:: bash

               ./deploy_platform.sh --offline --chart-path kaapana-admin-chart-<version>.tgz


#. The script requires several inputs from you:

   1. *server domain (FQDN):*

      You should enter the **domain, hostname or IP-address** where the server is accessible from client workstations.
      **Keep in mind, that valid SSL-certificates are only working with FQDN domains.**

   2. *Enable GPU support?*

      Answer *yes* if you have a Nvidia GPU, installed drivers and enabled GPU for Microk8s.

   3. *Please enter the credentials for the Container-Registry:*

      Use the credentials to your own registry or the ones provided to you by the Kaapana team.

#. As soon as the script finished successfully you will see the following output:

   .. code-block:: bash

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

#. As all docker images are pulled from the container registry, it may take a while until all pods are running.
   You can check the progress with:

   :code:`watch microk8s.kubectl get pods -A`
   
   When all pods are in the "running" or "completed" state, you can visit the platform at the given domain.

.. _platform_config:

Platform Configurations
^^^^^^^^^^^^^^^^^^^^^^^

During the build process the file :code:`.kaapana/build/kaapana-admin-chart/deploy_platform.sh` is generated.
This section provides a brief explanation about the multiple variables in :code:`deploy_platform.sh` which can be changed to configure the Kaapana platform for different use cases.

Some of the variables are automatically set during the build process.

Platform and registry configurations
------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 10 50

   * - Variable
     - Default
     - Type
     - Description
   * - ``PLATFORM_NAME``
     - ``"kaapana-admin-chart"``
     - string
     - Name of the Helm chart for the platform.
   * - ``PLATFORM_VERSION``
     - ``$( git describe )``
     - string
     - Version for the Helm chart. Automatically set to the output of ``git describe`` in your Kaapana repository.
   * - ``CONTAINER_REGISTRY_URL``
     - ``""``
     - string
     - Container registry URL, like ``dktk-jip-registry.dkfz.de/kaapana`` or ``registry.hzdr.de/kaapana/kaapana``. Set from ``default_registry`` in ``build-config.yaml``.
   * - ``CONTAINER_REGISTRY_USERNAME``
     - ``""``
     - string
     - Registry username. Set automatically if ``include_credentials: true`` in ``build-config.yaml``.
   * - ``CONTAINER_REGISTRY_PASSWORD``
     - ``""``
     - string
     - Registry password. Set automatically if ``include_credentials: true`` in ``build-config.yaml``.

Deployment configurations
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 10 50

   * - Variable
     - Default
     - Type
     - Description
   * - ``DEV_MODE``
     - ``"true"``
     - string
     - If true, sets ``imagePullPolicy: "Always"``; images are re-downloaded on pod restart. If false, uses ``"IfNotPresent"`` and pre-configures password policies in Keycloak.  
       **NOTE:** If ``OFFLINE_MODE="true"``, ``imagePullPolicy="IfNotPresent"`` regardless of ``DEV_MODE``.
   * - ``GPU_SUPPORT``
     - ``"false"``
     - string
     - Enables NVIDIA GPU support if available (checks ``nvidia-smi``).
   * - ``PREFETCH_EXTENSIONS``
     - ``"false"``
     - string
     - If true, installs extensions listed in ``deployment_config.yaml`` under ``preinstall_extensions``.
   * - ``CHART_PATH``
     - ``""``
     - string
     - Absolute path to platform chart (.tgz). Required in offline mode. Setting this also sets ``PREFETCH_EXTENSIONS="false"``.
   * - ``NO_HOOKS``
     - ``""``
     - string
     - Flag for ``helm uninstall``. Use ``"--no-hooks"`` to disable pre/post delete jobs.
   * - ``ENABLE_NFS``
     - false
     - bool
     - Enables ``storageClassName: nfs`` for persistent volumes.
   * - ``OFFLINE_MODE``
     - false
     - bool
     - If true, ``CHART_PATH`` is required. Also sets ``imagePullPolicy="IfNotPresent"``.

Namespace configurations
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 10 50

   * - Variable
     - Default
     - Type
     - Description
   * - ``INSTANCE_UID``
     - ``""``
     - string
     - Prefix for namespace variables (e.g., ``SERVICES_NAMESPACE``) and suffix for ``FAST_DATA_DIR`` and ``SLOW_DATA_DIR``.
   * - ``SERVICES_NAMESPACE``
     - ``"services"``
     - string
     - Kubernetes namespace for Kaapana apps (e.g., airflow, backend, extensions).
   * - ``ADMIN_NAMESPACE``
     - ``"admin"``
     - string
     - Namespace for core components like proxy and auth.
   * - ``EXTENSIONS_NAMESPACE``
     - ``"extensions"``
     - string
     - Currently not used.
   * - ``HELM_NAMESPACE``
     - ``"default"``
     - string
     - Helm namespace used for platform charts.

Resource configurations
------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 10 50

   * - Variable
     - Default
     - Type
     - Description
   * - ``PACS_PERCENT``
     - 30
     - int
     - % of allocable memory (70% of total) allocated to PACS.
   * - ``AIRFLOW_PERCENT``
     - 50
     - int
     - % of allocable memory for Airflow workflow system.
   * - ``OPENSEARCH_PERCENT``
     - 20
     - int
     - % of allocable memory for Opensearch metadata and search system.

Data configurations
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 10 50

   * - Variable
     - Default
     - Type
     - Description
   * - ``FAST_DATA_DIR``
     - ``"/home/kaapana"``
     - string
     - Directory for stateful application data (e.g., databases, tmp).
   * - ``SLOW_DATA_DIR``
     - ``"/home/kaapana"``
     - string
     - Directory for long-term data storage like DICOM files.


Credentials
---------------------------------

.. important::

   The following variables are used as credentials for system users for components within the platform.
   They **must** be changed **before** running the deployment script.
   After deployment you cannot change them without breaking the platform.

.. list-table::
   :header-rows: 1
   :widths: 20 20 50

   * - Variable name
     - Default value
     - Description

   * - ``CREDENTIALS_MINIO_USERNAME``
     - ``"kaapanaminio"``
     - Username for Minio object storage.
   * - ``CREDENTIALS_MINIO_PASSWORD``  
     - ``"Kaapana2020"``
     - Password for Minio object storage.
   * - ``GRAFANA_USERNAME``
     - ``"admin"``
     - Username for Grafana dashboard.
   * - ``GRAFANA_PASSWORD``
     - ``"admin"``
     - Password for Grafana dashboard.
   * - ``KEYCLOAK_ADMIN_USERNAME``
     - ``"admin"``
     - Username for Keycloak administrator.
   * - ``KEYCLOAK_ADMIN_PASSWORD``
     - ``"Kaapana2020"``
     - Password for Keycloak administrator. **Minimum policy for production: 1 specialChar + 1 upperCase + 1 lowerCase and 1 digit + min-length = 8**

Initial Kaapana Login Credentials 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The initial credentials for the Kaapana platform are:

.. code-block:: bash

   username: kaapana
   password: kaapana    


In **production mode**, the initial credentials are:

.. code-block:: bash

   username: kaapana
   password: Kaapana2020!    



Undeploy Platform
^^^^^^^^^^^^^^^^^

To undeploy the Kaapana platform, the kaapana-platform-chart and all related charts need to be deleted. For that, run the deployment script :code:`./deploy_platform.sh` and choose the **2) Undeploy** option.

If the **undeployment fails**, make sure to manually check followint two things:

1. All helm charts are deleted. All helm charts in Kaapana are created with the same namespace so that they are distinguished from possible other charts

   :code:`helm ls -n kaapana`

2. All pods are deleted. Kaapana uses multiple namespaces for separating Kubernetes resources, i.e. **admin**, **services**, **project-xyz**.

   :code:`kubectl get pods -A`

.. hint::

   | The :code:`./deploy_platform.sh` script also has some flags that can help with failed undeployments.
   | :code:`--no-hooks` will purge all kubernetes deployments and jobs as well as all helm charts. Use this if the undeployment fails or runs forever.
   | :code:`--nuke-pods` will force-delete all pods of the Kaapana deployment namespaces.

