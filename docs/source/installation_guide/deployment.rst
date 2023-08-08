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
  | They can be adjusted in the :term:`deploy-platform-script` and can also be identical (everything is stored at one place).

The platform is deployed using the :term:`deploy-platform-script`, which you can find at :code:`kaapana/build/kaapana-admin-chart/deploy_platform.sh`.

Copy the script to your target-system (server) and **adjust it as described below**:

1. Open the :code:`deploy_platform.sh` script on the server
   
   :code:`nano deploy_platform.sh`

2. Have a look at the variables on top of the script. An explanation for all of the variables can be found below under **Platform configuration**.
   
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




Platform Config
^^^^^^^^^^^^^^^

During the build process the file :code:`.kaapana/build/kaapana-admin-chart/deploy_platform.sh` is generated.
This section provides a brief explanation about the multiple variables in :code:`deploy_platform.sh` which can be changed to configure the Kaapana platform for different use cases.

Some of the variables are automatically set during the build process.

Platform and registry configurations
------------------------------------

| :code:`PLATFORM_NAME` `(default: "kaapana-admin-chart", type: string)`
| Name of the Helm chart for the platform.
|

| :code:`PLATFORM_VERSION` `(default: "$( git describe )", type=string)` 
| Version for the Helm chart. Is automatically set to the output of :code:`git describe` in your kaapana repository.
|

| :code:`CONTAINER_REGISTRY_URL` `(default: "", type=string)` 
| Container registry URL, like `dktk-jip-registry.dkfz.de/kaapana` or `registry.hzdr.de/kaapana/kaapana`. Is automatically set to the value of :code:`default_registry` in your :code:`build-config.yaml`.
|

| :code:`CONTAINER_REGISTRY_USERNAME` `(default: "", type=string)` 
| Registry username. Is only set automatically, if :code:`include_credentials: true` in your in your :code:`build-config.yaml`.
|

| :code:`CONTAINER_REGISTRY_PASSWORD` `(default: "", type=string)` 
| Registry password. Is only set automatically, if :code:`include_credentials: true` in your in your :code:`build-config.yaml`.
|

Deployment configurations
--------------------------

| :code:`DEV_MODE` `(default: "true", type=string)` 
| If true, it will set :code:`imagePullPolicy: "Always"` for all kubernetes deployments and jobs. In other words, after every pod restart, associated images will be re-downloaded.
| If false, :code:`imagePullPolicy: "IfNotPresent"` and several password policies will be pre-configured in keycloak.
|

| :code:`GPU_SUPPORT` `(default: "false", type=string)` 
| Enable or disable NVIDIA GPU support for MicroK8s. Deployment script will check :code:`nvidia-smi` and set this to true if any GPUs are available.
|

| :code:`PREFETCH_EXTENSIONS` `(default: "false", type=string)`
| If set to true, this will install Kaapana extensions (specified in :code:`.kaapana/platforms/kaapana-admin-chart/deployment_config.yaml` under `preinstall_extensions`) along with the platform deployment.
|

| :code:`CHART_PATH` `(default: "", type=string)` 
| Absolute path for .tgz file of platform chart. Setting this path will deploy the platform in offline mode, in which case the images should be already present inside microk8s. 
| Providing a chart path will also set :code:`PREFETCH_EXTENSIONS="false"` and :code:`DEV_MODE="false"` and :code:`OFFLINE_MODE=true`.
|

| :code:`NO_HOOKS` `(default: "", type=string)`
| This value is inserted as a flag to :code:`helm uninstall` command while removing the platform chart. Only intendet non-emtpy value is :code:`"--no-hooks"`. This will disable all pre/post delete jobs.
|

| :code:`ENABLE_NFS` `(default: false, tpye=bool)`
| If true kubernetes persistent volumes will use :code:`storageClassName: nfs`.
|

| :code:`OFFLINE_MODE` `(default: false, tpye=bool)`
| Is automatically set to true, if :code:`CHART_PATH` is set.
|

Namespace configurations
---------------------------------

| :code:`INSTANCE_UID` `(default: "", type=string)` 
| This variable is used when multiple Kaapana instances are deployed on the same server. It is used as prefix for :code:`SERVICES_NAMESPACE`, :code:`JOBS_NAMESPACE`, :code:`EXTENSIONS_NAMESPACE` and :code:`HELM_NAMESPACE`. Additionally it is used as suffix for :code:`FAST_DATA_DIR` and :code:`SLOW_DATA_DIR`.
| 

| :code:`SERVICES_NAMESPACE` `(default: "services", type=string)` 
| The kubernetes namespace for all applications of a Kaapana platform, e.g. landingpage, airflow, minio, the kaapana-backend, installed extensions.
|

| :code:`ADMIN_NAMESPACE` `(default: "admin", type=string)`
| The kubernetes namespace for furndamental parts of a Kaapana platform, e.g. reverse proxy, authentication.
| 

| :code:`JOBS_NAMESPACE` `(default: "jobs", type=string)`
| The kubernetes namespace for pods that are started by airflow.
|

| :code:`EXTENSIONS_NAMESPACE` `(default: "extensions", type=string)`
| Currently not used.
| 

| :code:`HELM_NAMESPACE` `(default: "default", type=string)` 
| The helm namespace, where the platform charts are deployed. Note that it is different from the namespaces used for different types of Kubernetes resources on the cluster.
|


Data configurations
---------------------------------

| :code:`FAST_DATA_DIR` `(default: "/home/kaapana", type=string)` 
| Directory path on the server, where stateful application-data will be stored (databases, processing tmp data etc.).
|

| :code:`SLOW_DATA_DIR` `(default: "/home/kaapana", type=string)` 
| Absolute path for directory on the server, where the DICOM images and other data will be stored (can be slower).
|

Credentials
---------------------------------

 ============================ ============== ============
  Component                    Username       Password   
 ============================ ============== ============
  **Kaapana Login**            kaapana        kaapana    
  **Keycloak Administrator**   admin          Kaapana2020
  **Minio**                    kaapanaminio   Kaapana2020
  **Grafana**                  admin          admin      
 ============================ ============== ============

.. hint::
    | Most likely you will not need the Minio admin password. Use the ``Login with OpenID`` instead.  

