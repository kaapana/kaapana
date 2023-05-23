.. _platform_config:

Platform Config
===============

During the build process the file :code:`.kaapana/build/kaapana-admin-chart/deploy_platform.sh` is generated.
Inside :code:`deploy_platform.sh`, there are multiple variables available for configuring your Kaapana platform for different needs.
This section will give a brief explanation about these.
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
| The kubernetes namespace of all kubernetes service ressources.
|

| :code:`ADMIN_NAMESPACE` `(default: "admin", type=string)`
| The kubernetes namespace for all ressources that can be shared between multiple instances.
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