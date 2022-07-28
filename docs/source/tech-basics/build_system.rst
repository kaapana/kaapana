.. _kaapana_build_system:

How the build-system of Kaapana works
=====================================

This document focuses on the steps which are performed during the kaapana build process.
For details on how the build proccess is correctly started read :ref:`build`.
Assuming the kaapana repository was cloned into the :code:`kaapana/` directory the build process is usually 
started by executing 

:code:`python3 build-scripts/start_build.py -u <registriy_username> -p <registry_password>`

inside :code:`kaapana/`.

.. important:: 
    | This document expects a basic knowledge of the following technologies
    | - Docker_
    | - Kubernetes_
    | - Helm_

Configuration steps
-------------------

At first step a path to the kaapana repository is determined.
Then a config file is searched.
The config file can be specified in the command line with the flag :code:`-c, --config <path-to-config-file>`.
If no config file was specified in the command line a file called :code:`build-config.yaml` is searched in :code:`kaapana/build-scripts/`
If this file is not present it will be created based on :code:`build-config-template.yaml` and the build proccess exits with an error message.

Now all directories for external sources are checked if they are available.
Directories for external sources can either be specified in the command line after the flag :code:`-es, --external-sources <list-of-external-source-directories>` or in the config file as a comma-separated string for the key
:code:`external_source_dirs`.


Collecting available images and charts
--------------------------------------

Before the build process is initiated all available :code:`Dockerfiles` are recursively collected from the kaapana repository directory and all directories specified as external sources.
For each found Dockerfile an instance of the helper class :code:`Container` is initialized.
This step also checks if all required local images are present in the collection of images.

.. hint::

  **Local images**
  
  Not all images are pushed to the registry.
  If the Dockerfile contains the line :code:`LABEL REGISTRY="local-only"` the image is build but not pushed to the specified registry.
  It is tagged as :code:`local-only/<image-name>:<version>`.

In a similar manner the kaapana directory and all external source directories are scanned for :code:`Chart.yaml` files.
For each found file an instance of :code:`HelmChart` is initialized and if existing the .tgz file is removed.

Generating deployment scripts
-------------------------------

The next step is the creation of deployment scripts for each subdirectory of the :code:`kaapana/platforms/` directory.
The deployment script for the starter-platform for example can be found at :code:`kaapana/platforms/starter-platform/platform-deployment/deploy_platform.sh`.
It is based on :code:`kaapana/platforms/deploy_platform_template.sh` and configured according to a config file 
e.g. :code:`kaapana/platforms/starter-platform/platform-deployment/deployment_config.yaml`.

.. hint::

  **Platform charts**
  
  Currently there are two platforms build by default i.e. the :code:`starter-platform` and the :code:`kaapana-platform`.
  Each platform is entirely packaged as a single helm chart i.e. the :code:`starter-platform-chart` and the :code:`kaapana-platform-chart`.
  Platform charts are specified by the key-value pair :code:`kaapana_type: "platform"` in the :code:`Chart.yaml` file.
  
  A filter can be applied in order to build only a subset of platform-charts e.g. only the :code:`kaapana-platform-chart`.
  To do so use the command line flag :code:`-pf, --platform-filter <list-of-platform-chart-names>` or adjust the value of :code:`platform_filter` in the config file.


The actual build-proccess
-------------------------

The actual build-proccess consists of updating dependencies for helm charts, packaging and pushing helm charts and
of tagging, building and pushing images.
For each platform-chart that should be build the following steps are proccessed:

1. A dependecy tree of helm charts is generated
2. All helm charts in this tree are recursively packaged and the dependencies are updated, images associated with a chart are tagged in a uniform pattern
3. The platform-chart is packaged and pushed.
4. A list of images is generated in an order that allows to build them successively
5. A deployment script is generated
6. All images in the list generated in step 4 are build and all non-local images are pushed to the registry

.. hint:: 

    **Recursively proccessing charts**

    The basic component of step 2 is the static method :code:`create_build_version(chart)` of the :code:`HelmChart` class.
    The method is first called for the platform-chart and then recursively for each chart it depends on.
    This way all charts of the dependency tree are proccessed in a depth-first approach.
    It updates dependencies, packages charts and tags images.
    (For special charts specified as *collections* also an image is build and pushed by this method.)
    

.. hint:: 

    **Collections**

    A collection can be identified with an image and a helm chart.
    In the scope of the build script a collection contains several charts as dependencies.
    The build scripts processes a collection by updating the dependencies for all charts and packaging all charts it depends on.

.. hint:: 
    **Caching**
    
    All packaged charts and all information regarding the build process like the log file or the dependecy trees are stored in :code:`kaapana/build/`.


.. _Docker: https://www.docker.com/
.. _Kubernetes: https://kubernetes.io/
.. _Helm: https://helm.sh/