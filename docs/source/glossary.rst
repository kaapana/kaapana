.. _glossary:

Glossary
========

.. glossary::
    :sorted:

    platform
      A platform describes a system that runs on a remote server and is accessible via the browser. The :term:`kaapana-platform` is an example of a platform. Using kaapana, you can basically build your own platform by putting the services and extensions together that you need.
    
    kaapana-platform
      The kaapana-platform is an example platform with a default configuration that contains many of the typical platform components. This basic platform can be used as a starting-point to derive a customized platform for your specific project. 

    registry
      A registry is a storage and content delivery system, holding named Docker images, available in different tagged versions. 
    
    workflow
      A workflow in our definition is basically an Airflow DAG. It is a number of processing steps applied to a cohort of images. Synonyms used for :term:`"workflow<workflow>` are :term:`"pipeline"<pipeline>` or ":term:`"DAG"<dag>`". Some of the workflows are preinstalled in the platform. Other workflows can be installed and added via the :term:`extensions<extension>` to Airflow.

    application
      When we speak of an application we mean a tool or service that can be installed via the :term:`extensions<extension>` into a running platform. Moreover, an extension can be started and deleted and runs statically. An example of an application is jupyterlab.

    dag
      A DAG (Directed Acyclic Graph) is a python script describing an Airflow pipeline. It links multiple operators (output to input) to realize a multi-step processing workflow, typically starting with an operator that collects that data and ending with an operator that pushes the processing results back to some data storage.
    
    operator
      Each method or algorithm that is included in Kaapana as Docker container requires an associated Operator. An operator is a python script that can be included in an Airflow DAG as a processing step and interfacing the Docker container.
    
    server
      A dedicated physical or virtual machine with a supported operating system on which the platform can run.
    
    helm
      We use Helm to distribute and manage our Kubernetes configuration files. Like this we only need one helm chart that contains the whole platform. 

    chart
      A chart is a collection of Kubernetes files. E.g. there is a kaapana-platform chart, containing all configuration needed for the plain kaapana platform. However, also each extension is wrapped in a helm chart. 
    
    docker
      Docker is the technology that enables to integrate a whole OS system with all necessary requirements and a program itself into a so-called docker container. When running such a docker container only the physical resources of the host system are used. On Kaapana every service and workflow runs within a docker container.
       
    microk8s
      MicoK8s is a single-package lightweight :term:`kubernetes` tha we use to set up our :term:`kubernetes` cluster.

    kubernetes
      Kubernetes is an open-source container-orchestration system that we use to manage all the Docker containers that are needed for Kaapana.

    server-installation-script
      This script is used to install all required dependencies on the :term:`server`.
      It can be found within the Kaapana-repository: :code:`kaapana/server-installation/server_installation.sh`

      Currently the following operating systems are supported by the script:

      - Ubuntu 20.04
      - Ubuntu Server 20.04

      This script will do the following:

      1. Configure a proxy (if needed)
      2. Install packages if not present: snap, nano, jq and curl
      3. Install and configure :term:`microk8s`
      4. (opt) Enable GPU for :term:`microk8s` 
      5. (opt) Change the SSL-certificates 

      It will also add some commands to the :code:`.bashrc` of each user to enable a shortcut to the :code:`kubectl` command and to enable auto-completion.
    
    platform-installation-script
      This script is used to install a platform into the Kubernetes cluster. Basically this is done by installing the kaapana-platform chart. In addition, it can be used to reinstall, update and to uninstall the platform. Moreover, it can be used to update the extensions, to prefetch all docker containers needed for the extensions or to install certs. To see its full functionally simply execute it with the flag :code:`--help`. For changes on a running platform itself. execute it without any flag.   

    service
      Every docker container that runs statically inside in kaapana is service. Examples for services are Minio, OHIF, etc. 
    
    pipeline
      See :term:`workflow`

    single file and batch processing
      The difference between single and batch processing is that in single file processing for every image an own DAG is triggered. Therefore, each operator within the DAG only obtains a single image at a time. When selecting batch processing, for all the selected images only one DAG is started and every operator obtains all images in the batch. In general, batch processing is recommended. Single file processing is only necessary if an operator within the workflow can only handle one image at a time.

    extension
      Extensions are either workflows or applications that can be installed additionally on the platform.

    component
      ...

