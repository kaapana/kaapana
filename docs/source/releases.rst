
#########
Changelog
#########

.. _release-0.4.0:

------------------------

********************
Release Notes v0.4.0
********************

December 20, 2024

-------------------------

Data Separation
---------------
* Opensearch authentication with OIDC 
* Metadata exists in project context, i.e., project indices
* Minio authentication with OIDC
* Minio project bucket

Multiinstallable Applications in Project Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Multiinstallable applications like MITK Workbench, JupyterLab, 3D Slicer, and Tensorboard are adapted to the project context. Only users who are part of a project have access to applications that run in the corresponding project context. These applications receive their data from the dedicated project bucket in Minio.

When an admin launches an instance of a multiinstallable application from the Extensions view, the admin must select the correct project in the header of the website.

DicomWebFilter
^^^^^^^^^^^^^^
The DicomWebFilter enables series-level access control to DICOM data via a DicomWeb API. For example, two users can access the same DICOM study but only specific series within it. This is required in scenarios where a user generates segmentations for certain series of a study and does not want to share these segmentations.

The DicomWebFilter operates as a database storing access information and a REST API supporting the DicomWeb standard. Acting as an intermediary layer, it filters data received from a PACS based on the client’s access token and stored access rules.

A management API is also provided for updating access information.

Keycloak
^^^^^^^^

New Realm Roles and Groups
""""""""""""""""""""""""""
By default, the Kaapana realm in Keycloak includes three roles: :code:`admin`, :code:`project-manager`, and :code:`user`. Policies defining these permissions are managed via ConfigMaps in the auth-backend chart:

- :code:`admin`: Unlimited access to all APIs, routes, and objects.
- :code:`project-manager`: Full access to the project management API.
- :code:`user`: General access to Kaapana's non-system components and project-specific data based on roles.

Keycloak also includes the following groups, each inheriting specific roles:

- :code:`kaapana_admin`: Includes roles :code:`admin`, :code:`project-manager`, :code:`user`.
- :code:`kaapana_project_manager`: Includes roles :code:`project-manager`, `user`.
- :code:`kaapana_user`: Includes role :code:`user`.

Custom Token Mapper
^^^^^^^^^^^^^^^^^^^
Custom token mappers populate the client access token with project-specific claims, derived from the access information interface.

Access Information Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This interface includes:

* **Database**: Stores user, project, and permission data.
* **REST API**: Enables Keycloak token mappers to fetch permissions and manage stored information.

Main database objects:

- **Rights**: Key-value claims for access tokens.
- **Projects**: Projects bundle the information.
- **Roles**: Collections of rights mapped to users and projects.
- **UsersProjectsRoles**: Links users, roles, and projects. A user can only have a single UsersProjectsRoles mapping per project. But a user can be mapped to the same role for multiple projects.

Example: If a role that contains the right {"claim_key": "opensearch", "claim_value": "admin_project"} is mapped to user A in Project foo, the access token of user A will contain the claim :code:`"opensearch": ["admin_project_foo"]`. Opensearch is configured accordingly to look for backend-roles in the opensearch claim of the access token and to know which permissions to grant users with the respective roles.

Initial rights, roles, projects and respective mappings can be configured in the `access-information-interface-config <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/release/0.4.0/services/data-separation/access-information-interface/access-information-interface-chart/templates/configmap.yaml>`_ . Per default version 0.4.0 comes with only one project role, i.e. :code:`admin`. This role grants access to the project bucket in Minio and the project index in opensearch.

Workflow Execution
^^^^^^^^^^^^^^^^^^
* Requests to the Kaapana backend must include a Project-Name cookie or project header.
* Processing containers run in dedicated Kubernetes project namespaces.
* Introduced :code:`kaapanapy` package in base-python-cpu image.
* Operators use project-system-user credentials for authentication to to DicomWebFilter, MinIO and Opensearch.

Project-Based UI
----------------
* Workflow menu requires a selected project.
* Selected project is stored in VueStore and browser cookies.
* Gallery View only shows series that are part of the selected project.
* The confiuraton of any job is extended with a :code:`project_form` that has information about the selected project from which the workflow was started.
* "Active Applications" view shows all multiinstallable applications that are started within the selected project context.
* "Workflow Results" view displays data only from the corresponding project bucket.

Project Management UI
^^^^^^^^^^^^^^^^^^^^^
A new project management UI is introduced for viewing all available projects for the user. Admin users can create new projects and add/update/delete users to/from projects.

Project-Based Data Ingestion
----------------------------
Incoming data assignments depend on calling and called AE title conventions (:code:`kp-<project-name>` and :code:`kp-<dataset-name>`). Both arguments have a size limit of 16 chars, modify conventions via the :code:`LocalSanitizeProjectAndDatasetOperator`.

Extension Development Kit (EDK)
-------------------------------
* New application for developing and deploying extensions within Kaapana.
* Includes VSCode-based development environment and local registry.
* Build container images and Helm charts inside the environment and deploy them directly to the platform.

Deploy Script
-------------
* Configurable memory resources for PACS, OpenSearch, and Airflow.
* Ensures stuck Helm charts are deleted during undeployment.

Workflow List
-------------
* Introduced pagination.

DICOM Validation
----------------
* Validates incoming DICOM files, showing error and warning counts.
* Supports :code:`dciodvfy` and :code:`dicom-validator`.
* Stores validation reports in MinIO with a configurable whitelist for excluded tags.

DAGs
----
* nnUNet workflows updated to v2.
* Added service DAG for workflow result notifications.
* DICOM validation DAGs support manual revalidation.

Custom Registry Secrets
-----------------------
* New application for pulling from multiple registries apart from the one that the Kaapana instance is deployed from
* Allows adding secrets of new registries to Kubernetes

Operators
---------
* Containerized local operators (e.g., :code:`GetInputOperator`, :code:`MinioOperator`).
* Refactored helper modules in :code:`kaapanapy.helper`.
* Added CI/CD tests for operators.

Bug Fixes
---------
* Fixed :code:`patient_age` inconsistencies in :code:`LocalDcm2JsonOperator`.
* :code:`dicom-init` now waits until opensearch is ready
* :code:`init-extensions` job has better monitoring for failed pods
* and many more

Updates and Security Fixes
--------------------------
* Microk8s to :code:`v1.31`
* Base image to :code:`Ubuntu:24.04`
* Base python to :code:`3.12`
* Base postgres to :code:`17.2`
* MITK to :code:`v2024.12`
* Airflow to :code:`2.10.3`
* Minio to :code:`2024-11-07`
* Opensearch to :code:`2.18.0`
* Dcm4chee to :code:`5.33.1`
* Prometheus to :code:`v3.0.0`
* Grafana to :code:`11.3.1`
* Open Policy Agent to :code:`0.70.0`
* Added security headers and middleware: (e.g. `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`)
* and more

Removed features
----------------
* nnUNet v1 and its pretrained models are no longer supported, the default version is v2
* The dag :code:`train-with-pretrained-weights` is removed
* The extension :code:`external-pacs` remove due to refactor changes

.. _release-0.3.5:

-------------------------

********************
Release Notes v0.3.5
********************

September 11, 2024

-------------------------

Bug fixes
---------

* Build fix - wsi-converter dependency link updated
* Removed breaking LocalDiceOperator from nnUNet
* Fix file opening issue in Collabora for nested files


.. _release-0.3.4:

-------------------------

********************
Release Notes v0.3.4
********************

July 15, 2024

-------------------------

Bug fixes
---------

* Fixes offline deployment caused by wrong NVIDIA gpu-operator version
* Fixes requirements file for operator trigger-ansible-playbook
* Fixes missing requirements for OtsusNotebookOperator


.. _release-0.3.3:

-------------------------

********************
Release Notes v0.3.3
********************

May 29, 2024

-------------------------

Bug fixes
---------

* Fixes broken build due to breaking changes in vueuse/core 10.10.0


.. _release-0.3.2:

-------------------------

********************
Release Notes v0.3.2
********************

May 24, 2024

-------------------------

Bug fixes
---------

* Fixes landing page UI dev-mode
* Removes mechanism to add access control ids from HelperDcmWeb and LocalDicomSendOperator
* Fixes patient age inconsistency bug in LocalDcm2JsonOperator
* Adds local tests to CI/CD pipeline

Documentation
-------------

* Adds links of main GitLab repository and YouTube channel in README

.. _release-0.3.1:

-------------------------

********************
Release Notes v0.3.1
********************

April 22, 2024

-------------------------

Bug fixes
---------

* Fixes dcm4chee import image bug, by pinning image container hash and dcm4chee-postgres git commit hash

.. _release-0.3.0:

-------------------------

********************
Release Notes v0.3.0
********************

April 15, 2024

-------------------------
 
DAGs and Operators
------------------
* advanced-collect-metadata workflow
* modify-dcmseg workflow
* nnunet-training
    * integrated label renaming, fusing, keeping/ignoring functionality
    * warm-start functionality for fine-tuning pre-trained model
* nnunet-ensemble
    * integrated label renaming, fusing, keeping/ignoring functionality
    * new evaluation metrics
* evaluate-segmentations: new DAG for evaluating predicted segmentations with ground truth
* train-with-pretrained-weights: new DAG for training nnunet and classification workflows starting with pretrained model weights
* download-selected-series: now allows downloading DICOMs as NIFTIs
* Introduce `JupyterlabReportingOperator`
* Adjust radiomics-federated, nnunet-training and nnunet-ensemble to use JupyterLabReportingOperator instead of custom processing-operators.
* Introduce LocalVolumeMountOperator to transfer data between container file systems and PersistentVolumes
* Adapt DAGs `import-dicoms-in-zip-to-internal-pacs`, `convert-niftis-to-dicoms-and-import-to-pacs` and `WSI-import` to get data from PersistentVolume instead of MinIO Bucket.

KaapanaFed
----------
* FedDC as FL aggregation method
* federated radiomics workflow
* federated advanced-collect-metadata workflow

Workflow Management System
--------------------------
* Workflow List:
    * operator state reporting in Job List
    * restarting/stopping service jobs
* Instance overview:
    * easier instance registration
* Data Upload:
    * Adjust upload mechanism to store data in PersistentVolume instead of MinIO

Extensions
----------
* specify links in values.yaml of extensions to overwrite ingress paths
* option to filter by resources in the UI
* New Collabora extension to view and edit office documents in the platform

Bug Fixes
---------
* LocalDcm2JsonOperator.py (Importing .dcm metadata)
    * Fixed an issue when LocalDcm2JsonOperator errors on valid .dcm files with valid symbols like ^%+
    * LocalDcm2JsonOperator now correctly parses all valid formats of datetime, time and date
    * LocalDcm2JsonOperator now correctly identifies Sequence keyword as `object` not `object_object`
* Fix bodypart regression opencv-python-headless version
* Fix issue when downloading models for bodypart regression
* Fix path to source files for pixelmed in wsiconv
* Fix logging error in pod_launchyer.py
* Fix proxy configuration in server installation script

MinIO
-----
* Introduce new local-only/base-minio-mc image with minio client
* Introduce minio-mirror image to provide minio bucket data to volume mounts
* Adjust staticwebisteresults to provide files from mirrored minio bucket
* Adjust applications to get filesystem data from mirrored minio buckets
* Refactor minio-init to use base-minio-mc image
* Introduce new policy: KaapanaUser for restricted access to all buckets but upload.

Meta-dashboard
--------------
* Removed modality chart graph from the metadashboard

Keycloak
--------
* Keycloak roles and attributes are inherited from group `kaapana_user` and `kaapana_admin`
* Assign new minio policy KaapanaUser to group kaapana_user
* Remove keycloak group `all_data`
* Add role user to default_roles_kaapana

Dcm4chee
--------
* Introduce reverse-proxy in front of dcm4chee for access control
* Introduce mechanisms to assign access control ids to studies and AEs in dcm4chee

Authorization and security
--------------------------
* Introduce open policy agent as policy decision point.
* Introduce system user for impersonation.
* Add network policy to restrict access to the kube-api server
* Run containers for landing-page, staticwebsiteresults, jupyterlab and tensorboard as non-root users
* Implement impersonation and authorization mechanism in HelperMinio.py and adjust kaapana-backend and operators.
* Implement impersonation and authorization mechanism in HelperDcmWeb.py and adjust operators.
* Refactor access control and authorization in the landingpage
* Adding idle timeout processed by frontend in the landingpage
* Add new ClusterRole for the kubernetes-dashboard in production systems

Updates and Security Fixes
--------------------------
* Update MicroK8s v1.28
* Base Image to Ubuntu:22.04
* Base Postgres to 15.6-alpine
* Base python to version 3.10
* Updated alertmanager:v0.25.0
* Updated statsd-exporter:v0.23.1
* Updated Grafana:9.4.7
* Updated opensearch:2.12.0
* Updated open-policy-agent:0.62.0
* Updated OHIF v3.7
* Updated Mitk 2023.12
* Update Apache Airflow 2.8.4
* Update MinIO to RELEASE.2024-01-29T03-56-32Z
* and many more

.. _release-0.2.6:

-------------------------

********************
Release Notes v0.2.6
********************

January 09, 2024

-------------------------

Bug fixes
---------

* Fix behaviour when missing filename or '---' in filenames in Bin2DcmOperator 
* Changed storaged path for TotalSegmentator radiomics results from 'thumbnail' to 'totalsegmentator'

.. _release-0.2.5:

-------------------------

********************
Release Notes v0.2.5
********************

October 26, 2023

-------------------------

Bug fixes
---------

* Fix issue downloading Body Part Regression models from Zenodo
* Fix a problem when importing uploaded container images

.. _release-0.2.4:

-------------------------

********************
Release Notes v0.2.4
********************

September 11, 2023

-------------------------

Bug fixes
---------

* Fix problem of images stuck in CTP on large imports
* Fix python requirements for bodypart-regression processing container

.. _release-0.2.3:

-------------------------

********************
Release Notes v0.2.3
********************

August 15, 2023

-------------------------

Bug fixes
---------

* Fix of circular import in Airflow
* Fixes in charts_helper.py
* Fixes in offline installation of microk8s
* Fix in deploy_platform.sh script
* Fix in gallery view

.. _release-0.2.2:

-------------------------

********************
Release Notes v0.2.2
********************

July 26, 2023

-------------------------

Bug fixes
---------

* Installation of certificates
* Access to Traefik routes for users with no admin rights

.. _release-0.2.1:

-------------------------

********************
Release Notes v0.2.1
********************

July 19, 2023

-------------------------

New features
------------

* Major restructuring and update of the documentation
* Added experimental persistent layer as extension for data management
* Updated landing page layout
* RTStruct and segmentation support in Gallary View

Bug fixes
---------

* Redirect for Minio and Keycloak
* Update of constraints file
* Fix of TypeError: cannot pickle '_thread.lock' object in Airflow
* Muliplte fixes in Kaapana-Backend
* Fixes in Trivy vulnerability scanner
* Fixes in the server_installation.sh
* Muliplte fixes in Kube-Helm backend
* Introducing a smaller GPU base image
* Fixes in scheduling of workflows
* Fix of Prometheus and Grafana error
* Fix in data upload
* Removal of not ready extensions from collections chart
* Fix of Tensorboard logs
* Fix of nnU-Net ensemble workflow
* Fix of radiomics federated workflow

Upcoming
--------

* Maintenance UI for UI-based platform management and maintenance 
* Multi Instance support for different Kaapana deployments within a single K8S Cluster
* New persistence layer for Kapaana

.. _release-0.2.0:

-------------------------

********************
Release Notes v0.2.0
********************

May 18, 2023

-------------------------

New Features
============

.. figure:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/img/datasets.png
   :align: center
   :alt: New Dataset UI


Datasets
--------

* Added intuitive Gallery-style view visualizing thumbnails and (configurable) metadata of DICOM Series
* Added Multiselect which allows performing actions on multiple series at once including add/removing to/from a dataset, executing workflows on individual series or creating new datasets based on the selection
* Added configurable side panel metadata dashboard allowing the exploration of metadata distributions (based on selections)
* Introduced intuitive shortcut based tagging functionality allowing fast and convenient annotation and categorization of series
* (Full-text) search to filter for items based on metadata
* Added option to open a series in a side panel visualizing the DICOM using (an adjusted) OHIF Viewer-v3 next to all Metadata of the specific series.

Workflow Management System:
---------------------------

* Introduction of Kaapana Object "Workflow"
* Workflows semantically bind together multiple jobs, the data on which the jobs are running on and the orchestrating/triggering and the runner instances of the jobs Workflow Execution
* Only location to trigger executable jobs on Kaapana platform
* Directly accessible from Datasets view
* Remote/federated workflow execution on connected remote Kaapana instances more built-in

Workflow List:

* Visualizes all workflows which are or were running on the platform including
* Information regarding the workflow specification live status updates of workflow's jobs
* Workflow actions to abort, restart or delete workflows including all their jobs
* Information regarding the job specification
* Live updates of the job's status
* Redirect links to the job's airflow DAG run
* Job actions to abort, restart or delete jobs

Instance Overview:

* Visualization of the local and remote Kaapana instance
* Connection of remote Kaapana instances
* Information regarding the instance specification


Extension Upload / Data Upload mechanism
----------------------------------------
* Introduction of new NIfTI + DICOM upload (NIfTIs will be converted to DICOM + incl. segmentation support)
* Easily importing the uploaded images into PACS via available workflows
* New chart (.tgz) and container (.tar) upload feature which enables users to upload their own extensions into the platform
* Importing container .tar files directly into the microk8s container runtime


Results page
------------
* A new results page has been introduced which allows users to explore results of their workflows by visualizing HTMLs 

MISC:
-----

* New NIfTI + DICOM upload (NIfTIs will be converted to DICOM + incl. segmentation support)
* New extension and container upload & import features
* Improved landing-page navigation to make workflows more present and more intuitive to interact with
* git-describe-based versioning for Kaapana
* Switch to `persistent-volumes <https://kubernetes.io/docs/concepts/storage/persistent-volumes/>`_ for better security and better cloud provider support 
* Security vulnerability improvements
* Included `Trivy <https://trivy.dev//>`_ container scanning for automatic CVE detection + SBOM creation in the build system
* Improved security check for all ingress requests
* Improved Keycloak initialization & password policy for production mode
* Introduced Black code formatter for Kaapana
* Introduction of a dark mode to the landing page
* Introduction of new base images for better dependency management and security handling (also smaller and more efficient)
* Improved Airflow scheduling for Kubernetes jobs
* Split of Airflow scheduler and webserver in separate PODs for better stability and robustness
* Automatic thumbnail generation for RTSTRUCTs and DICOM SEGs
* Improved annotation-metadata detection for SEG and RTSTRUCT
* Improved Kaapana build-system to better support external resources and platform creation
* Better support for offline installation & VM creation (upcoming)
* Many other smaller bug-fixes, improvements and adjustments

New Workflows
-------------

* `TotalSegmentator <https://github.com/wasserth/TotalSegmentator>`_ incl. all sub-tasks
* RTSTRUCT support for nnUNet training
* nnU-Net federated
* Radiomics federated

Updated Components
------------------

* Kubernetes v1.26/stable
* Helm v3.10
* Airflow v2.5.3
* Keycloak v21.0.1
* Traefik v2.9.9
* Grafana v9.4.7
* Kubernetes Dashboard v2.7.0
* OHIF v4.12.26
* Prometheus v2.34.0
* Alertmanager v0.25.0
* Auth2-proxy v7.4.0
* metrics-scraper : v1.0.9
* kube-state-metrics: v2.8.2
* OpenSearch Dashboards: 2.6.0
* OpenSearch: v2.6.0


New Extensions
--------------

* 3D Slicer
* Model-Hub
* RateMe


Upcoming
--------

* Maintenance UI for UI-based platform management and maintenance 
* Multi Instance support for different Kaapana deployments within a single K8S Cluster
* New persistence layer for Kapaana

.. _release-0.1.3:

---------

********************
Release Notes v0.1.3
********************

Date: July 31, 2022

---------

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

