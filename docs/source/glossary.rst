.. _glossary:

Glossary
########

.. glossary::
    :sorted:

    DNS
      The Domain Name System (DNS) is the phonebook of the Internet. 
      Humans access information online through domain names, e.g. www.dkfz.de. 
      Web browsers interact through Internet Protocol (IP) addresses. 
      A DNS translates domain names to IP addresses so browsers can load Internet resources.
    
    platform
      A platform describes a system that runs on a remote :term:`server` and is accessible via the browser. 
      The :term:`kaapana-platform` is an example of a platform. 
      Kaapana empowers you to construct a customized platform by integrating the services and extensions you require, tailoring it precisely to your needs.
    
    kaapana-platform
      The kaapana-platform is a :term:`platform` that comes with all required base components like a reverse-proxy and an authentication provider as well as many usefull :term:`services<service>` like Airflow, MinIO and the :term:`workflow-management-system`. 
      You can utilize this platform as a starting-point to derive a customized platform for your specific project.

    registry
      A registry is a storage and content delivery system holding container images and :term:`Helm<helm>` :term:`charts<chart>` available in different tagged versions. 
      A registry can be private or public. Examples of such registries are, `DockerHub <https://hub.docker.com/>`_ and Elastic Container Registry (ECR) provided by Amazon's AWS. `GitLab <https://about.gitlab.com/>`_ offers free, private registries.
    
    deployment
      A Kaapana deployment is a :term:`kaapana-platform` that was deployed on a :term:`server` using the :term:`deploy-platform-script`. 
      This is not the same as a deployment in the scope of :term:`Kubernetes<kubernetes>`, where a deployment is an object that is used to manage multiple `pods`. 
      In fact a Kaapana deployment consists of multiple Kubernetes deployments.

    workflow
      Workflows semantically bind together multiple :term:`jobs<job>`, their processing data, and the orchestration/triggering and :term:`runner-instances<runner-instance>` of those jobs. 
      Workflows can be started via the tab `Workflow Execution` in the :term:`workflow-management-system`. 
      In the `Workflow List` tab you can view information about worfklows and their jobs. 
      Some workflows are preinstalled in the platform, others can be installed as :term:`extensions<extension>`.

    application
      In the scope of Kaapana an application is a tool or service that can be installed as an :term:`extension<extension>` into a running platform. 
      Moreover, an application can be started and deleted and runs statically. 
      An example of an application is JupyterLab.

    dag
      A DAG (Directed Acyclic Graph) is an Airflow pipeline that is defined in a python script. 
      It links multiple :term:`operators<operator>` (output to input) to realize a multi-step processing workflow, typically starting with an operator that collects that data and ending with an operator that pushes the processing results back to some data storage. 
      An instance of a running DAG is called DAG-run.
    
    operator
      An Airflow operator is a Python class that represents a single task within a :term:`DAG<dag>`. 
      This allows for the reuse of operators as building blocks across multiple DAG definitions. 
      Operators can also run tasks by running a :term:`container<container>`. 
      This makes the execution of operators heavily scalable.
    
    server
      A dedicated physical or virtual machine with a supported operating system on which a :term:`platform` can run.
    
    helm
      We use Helm to distribute and manage our :term:`Kubernetes<kubernetes>` configuration files. 
      Like this we only need one Helm chart that contains the whole platform i.e. the :term:`kaapana-admin-chart`. 

    chart
      A :term:`Helm<helm>` chart is a collection of :term:`Kubernetes<kubernetes>` files. 
      The :term:`kaapana-admin-chart` consists of all the configuration required for the :term:`kaapana-platform`. 
      Moreover, each :term:`extension` and :term:`service` is packaged within a Helm chart. 
    
    kaapana-admin-chart
      This :term:`Helm<helm>` chart consists of all :term:`Kubernetes<kubernetes>` configuration required for the :term:`kaapana-platform`.
      It contains the fundamental features of the platform such as reverse proxy, authentication, and kube-helm backend. It has :term:`kaapana-platform-chart` as a sub-chart.

    kaapana-platform-chart
      This :term:`Helm<helm>` chart consists of most of the interactive components of Kaapana, such as Airflow, PACS, Minio, landing page and Kaapana backend.
    
    containerd
      We use `containerd <https://containerd.io/>`_ as runtime environment for the :term:`containers<container>` in the :term:`Kubernetes<kubernetes>` cluster.
      It manages the lifecycle of a container.

    container
      A container is a self contained virtual environment that runs a software along with the code and all of its dependencies.
      In this way, it can run quickly and reliably on any environment.
      We utilize :term:`containerd` to run containers.
      In Kaapana, every :term:`service` and :term:`job` runs within a container.
      Containers are specified by container images that are :term:`built<build>` according to a file e.g. a Dockerfile.
         
    build
      A build describes the process of building :term:`container`-images from files like Dockerfiles.
      Images for Kaapana can be build using tools like `Docker <https://www.docker.com/resources/what-container/>`_ or `Podman <https://docs.podman.io/en/latest/>`_.
    
    microk8s
      MicoK8s is a lightweight, single-package :term:`Kubernetes<kubernetes>` distribution that we utilize to set up our Kubernetes cluster.

    kubernetes
      Kubernetes is an open-source container-orchestration system that we use to manage all the :term:`containers<container>` required for Kaapana.

    server-installation-script
      This script is used to install all required dependencies on the :term:`server`.
      It can be found within the Kaapana-repository: :code:`./kaapana/server-installation/server_installation.sh`.
      It will execute the following steps:

        1. Configure a proxy (if needed)
        2. Install packages if not present: snap, nano, jq, curl, net-tools, core18, helm
        3. Install, configure and start :term:`microk8s`
        4. Add alias for :code:`kubectl` to :code:`.bashrc` file and enable auto-completion
        5. (opt) Enable GPU for :term:`microk8s` 
        6. (opt) Change the SSL-certificates

      Currently supported operating systems:

        - Ubuntu 22.04
        - Ubuntu 20.04
        - Ubuntu Server 20.04
    
    deploy-platform-script
      This script is used to deploy a :term:`kaapana-platform` into a :term:`Kubernetes<kubernetes>` cluster or to undeploy a platform. 
      It basically installs the :term:`kaapana-admin-chart` using :term:`Helm<helm>`. 
      After building the platform you can find the script at :code:`./kaapana/build/kaapana-admin-chart/deploy_platform.sh`.

    service
      Every :term:`container` that runs statically inside a :term:`kaapana-platform` is a service. 
      Examples for services are Minio, OHIF, Airflow etc..
    
    pipeline
      See :term:`workflow`

    single file and batch processing
      The difference between single and batch processing is that in single file processing for every image an own :term:`job` is created. 
      Therefore, each :term:`operator` within the :term:`DAG` only obtains a single image at a time. 
      When selecting batch processing, a single :term:`job` is created for all selected images and every :term:`operator` obtains all images in the batch. 
      In general, batch processing is recommended. 
      Single file processing is only necessary if an operator within the :term:`DAG<dag>` can only handle one image at a time.

    extension
      Extensions are either :term:`workflows<workflow>` or :term:`applications<application>` that can be installed on the platform under the tab `Extensions` of the main menu.

    dataset
      A dataset is a list of dicom identifiers. Most workflows are executed on a dataset. Datasets can be managed in the :term:`data-curation-tool`.

    data-upload
      Data can be uploaded at the `Data Upload` tab of the :term:`workflow-management-system`. 
      After the upload has finished you can directly trigger special :term:`workflows<workflow>` on this data e.g. to convert nifti data to dicom or to import the data into the internal PACS.

    data-curation-tool
      The data curation tool is the place to view, curate and manage your :term:`datasets<dataset>`. 
      You can access it via the `Datasets` tab in the :term:`workflow-management-system`.
    
    workflow-management-system
      The workflow management system is the new environment for processing your data. 
      You can access it via the `Workflows` tab in the main menu. 
      Here you can upload data, use the :term:`data-curation-tool`, start a :term:`workflow`, get information about started workflows, and register :term:`runner-instances<runner-instance>`.
    
    runner-instance
      In the scope of federated processing a runner-instance is associated with the :term:`kaapana-platform`, where a :term:`job` is executed. 
      This must not be the same platform where the :term:`workflow` the job belongs to was executed. 
      You can add runner-instances under the tab `Instance Overview` of the :term:`workflow-management-system`.

    job
      A job belongs to a :term:`workflow` and is associated with a unique Airflow :term:`DAG-run<dag>`.

    NIFTI
      NIfTI (Neuroimaging Informatics Technology Initiative) is a data format for the storage of Magnetic Resonance Imaging (MRI) and other medical images.
      It provides a metadata header along with the actual volumes and is commonly used for research datasets and within scientific challenges. 

    DICOM
      Digital Imaging and Communications in Medicine (DICOM) is the standard for the communication and management of medical imaging information and related data.
      Since Kaapana is designed to integrate well with clinical medical imaging processes, DICOM is the primary data format of Kaapana and most workflows rely on data beeing present in the internal *PACS*.