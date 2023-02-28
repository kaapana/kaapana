
Changelog
#########

.. _release-0.1.3:

0.1.3
=====

Date: July 31, 2022

Changelog
---------

* Updated microk8s to v1.23/stable
    * latest stable version
    * API adjustments within all deployments

* Server and platform installation improvements
    * new certificate installation incl. random cert generator
    * easy offline installation method (no registry needed)
    * introduction of a helm namespace for separate deployment tracking
    * support for custom DNS servers
    * better proxy support (incl. no_proxy configuration)
    * improved security by RBAC cluster support
    * support for AlmaLinux as a replacement for CentOS 8

* Extensions
    * simplification of extension collections

* New build-system
    * improved build-time (~1h for the kaapana-platform)
    * improved dependency checks
    * build-tree visualization
    * container tarball export for offline installation
    * platform filters (to only build specific ones)
    * ability to include external repositories into the build-tree
    * Podman support as Docker alternative
    * direct microk8s injection
    * stats on used / unused resources
    * better logs
* ability to separate platforms in a registry using prefixes

* New processing scheduling system
    * improved robustness
    * multi GPU support
    * multi job per GPU support
    * utilizes Airflow pools as a transparent and consistent solution

* New Auth-Proxy → now OAuth2-proxy (Louketo has been deprecated)
* No additional port for Keycloak needed anymore
* Support for http → https redirect for arbitrary ports
* New development method within running pipelines
    * live container-debugging during workflow execution
    * Front-end for build-in IDE within the platform

* Bug-fixes
    * Fixed misbehaving “Delete-Series-From-Platform” workflow
    * Re-Index workflow
    * Increased timeout for process incoming dcm when called from CTP
    * Fixed bug in DICOM reindexation polluting the data directory
    * Fixed bugs in install script to make it location agnostic

* General Improvements
    * More robust un-deployment of the platform
    * Up to date Zenodo metadata
    * New tagging system allowing the deletion of tags and a faster processing
    * Adjustments of the landing page design
    * The dcmsend processing container reties sending of images up to 5 times making it more robust
    * Add Monitoring support for airflow
    * New Grafana Dashboards for Airlfow, Kubernetes and Traefik

* Documentation
    * Adjusted tutorials
    * New Operator docs
    * New Guides (Write Dockerfiles for Kaapana, Automatic Triggering, Send images to platform, Building the Platform, How does the Build System Work, Provide Workflow as Extension, How Kaapana uses Helm Charts, How to stop and restart a workflow, How to remove data from the platform, How to backup a Kaapana instance, How to install TLS certificates)
    * FAQ extension
    * New examples for workflows and processing containers
    
* many other smaller bug-fixes and adjustments

Incompatible Changes
--------------------

* Kubernetes v1.19 is not supported anymore

Updated Components
------------------

* Airflow v2.2.5
* Dcm4chee v5.26.0
* Keycloak v19.0.3
* Traefik v2.6
* Kubernetes Dashboard v2.5.1
* OHIF v4.12.26
* MinIO v2022.03.26
* Grafana v8.4.4
* Prometheus v2.34.0
* Alertmanager v0.24.0
* CTP v0.1.3
* kube-state metrics v2.5.0

Extensions
----------

New integrations:

* openEDC 
* doccano-image-tagging
* Federated learning extension

Updated extensions:

* Jupyterlab v3.3.2
* Code-Server v4.2.0
* Tensorboard v2.8.0
* Mitk-Workbench v2022.04


0.1.3-beta
==========

Date: May 30, 2022

0.1.2
=====

Date: May 15, 2022

* Last release with support for kubernetes v1.19 

0.1.0
=====

Date: Oct 24, 2020

* Initial release of Kaapana

