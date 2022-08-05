.. _platform_config:

Platform Config
===============

Inside :code:`deploy_platform.sh`, there are multiple variables available for configuring Kaapana platform for different needs. This section will give a brief explanation about these.

Main platform configuration
---------------------------

| :code:`PROJECT_NAME` `(default: "kaapana-platform-chart", type: "string")`
| Name of the Helm chart for the platform
|

| :code:`DEFAULT_VERSION` `(default: "0.1.3", type="string")` 
| Version for the Helm chart
|

| :code:`PROJECT_ABBR` `(default: "kp", type="string")` 
| Abbrevention of the platform. This is passed to all docker images used inside deployments, and should be the same as the ones used while building containers. The naming rule for images on a registry is as follows: 
| `<CONTAINER_REGISTRY_URL>/<image-name>:<PROJECT_ABBR>_<DEFAULT_VERSION>__<image-version>` 
|

| :code:`CONTAINER_REGISTRY_URL` `(default: "", type="string")` 
| Container registry URL, like `dktk-jip-registry.dkfz.de/kaapana` or `registry.hzdr.de/kaapana/kaapana`. Needs to be set for online deployment, the registry will be used to pull the built charts and containers
|

| :code:`CONTAINER_REGISTRY_USERNAME` `(default: "", type="string")` 
| Registry username
|

| :code:`CONTAINER_REGISTRY_PASSWORD (default: "", type="string")` 
| Registry password
|

Deployment configuration
------------------------

| :code:`DEV_MODE` `(default: "true", type="bool")` 
| If true, it will set all PULL_POLICY parameters to "Always". In other words, after every pod or job restart, associated containers will be re-downloaded.
|

.. TODO: could not find any use for DEV_PORTS in any Helm chart or image
.. | :code:`DEV_PORTS` `(default: "false")`
.. |

| :code:`GPU_SUPPORT` `(default: "false", type="bool")` 
| Enable or disable NVIDIA GPU support for MicroK8s. Deployment script will check :code:`nvidia-smi` and set this to true if any GPUs are available 
|

| :code:`HELM_NAMESPACE` `(default: "kaapana", type="string")` 
| This namespace will be created via the helm install command. Note that it is different from the namespaces used for different types of Kubernetes resources on the cluster.
|

| :code:`PREFETCH_EXTENSIONS` `(default: "false", type="bool")`
| If set to true, this will install Kaapana extensions (specified in `deployment_config.yaml` under `preinstall_extensions`) along with the platform deployment.
|

| :code:`CHART_PATH` `(default: "false", type="string")` 
| Absolute path for .tgz file of platform chart. Setting this path will deploy the platform in offline mode, in which case the images should be already present inside microk8s. 
| Providing a chart path will also set :code:`PREFETCH_EXTENSIONS="false"` and :code:`DEV_MODE="false"`
|

| :code:`NO_HOOKS` `(default: "false", type="bool")`
| Inserts `--no-hooks` flag to :code:`helm uninstall` command while removing the platform chart. It will disable all pre/post delete jobs.
|

Individual platform configuration
---------------------------------

| :code:`FAST_DATA_DIR` `(default: "/home/kaapana", type="string")` 
| Directory path on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
|

| :code:`SLOW_DATA_DIR` `(default: "/home/kaapana", type="string")` 
| Absolute path for directory on the server, where the DICOM images and other data will be stored (can be slower)
|