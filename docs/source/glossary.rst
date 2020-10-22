.. _glossary:

Glossary
========

.. glossary::

    platform
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    kaapana-platform
      The kaapana-platform is an example platform with a default configuration that contains many of the typical platform components. This basic platform can be used as a starting-point to derive a customized platform for your specific project. 

    registry
      A registry is a storage and content delivery system, holding named Docker images, available in different tagged versions. 
    
    workflow
      A workflow in our definition is basically an Airflow DAG. It is a number of processing steps applied to a cohort of images. Synonyms used for workflow are pipeline or DAG.
    
    dag
      A DAG (Directed Acyclic Graph) is a python script describing an Airflow pipeline. It links multiple operators (output to input) to realize a multi-step processing workflow, typically starting with an operator that collects that data and ending with an operator that pushes the processing results back to some data storage.
    
    operator
      Each method or algorithm that is included in Kaapana as Docker container requires an associated Operator. An operator is a python script that can be included in an Airflow DAG as a processing step and interfacing the Docker container.
    
    server
      A dedicated physical or virtual machine with a supported operating system on which the platform can run.
    
    helm
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 

    chart
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    docker
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    microk8s
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 

    kubernetes
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    server-installation-script
      This script is used to install all required dependencies on the :term:`server`.
      It can be found within the Kaapana-repository: :code:`kaapana/server-installation/server_installation.sh`

      Currently the following operating systems are supported by the script:

      - Centos 8
      - Ubuntu 20.04
      - Ubuntu Server 20.04

      This script will do the following:

      1. Configure a proxy (if needed)
      2. Install packages if not present: snap, nano, jq and curl
      3. Install and configure :term:`microk8s`
      4. (opt) Enable GPU for :term:`microk8s` 
      5. (opt) Change the SSL-certificates 

      It will also add some commands the the :code:`.bashrc` of each user to enable a shortcut to the :code:`kubectl` command and to enable auto-completion.
    
    platform-installation-script
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    service
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    pipeline
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 

    component
      Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. 
    
    single file and batch processing
      The difference between single and batch processing is that in single file processing for every image an own DAG is triggered. Therefore, each operator within the DAG only obtains a single image at a time. When selecting batch processing, for all the selected images only one DAG is started and every operator obtains all images in the batch. In general, batch processing is recommended. Single file processing is only necessary if an operator within the workflow can only handle one image at a time.
