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
      In fact a Kaapana deployment consists of many Kubernetes deployments and other resources.

    workflow
      Workflows semantically bind together multiple :term:`jobs<job>`, their processing data, and the orchestration/triggering and :term:`runner-instances<runner-instance>` of those jobs. 
      Workflows can be started via the tab `Workflow Execution` in the :term:`workflow-management-system`. 
      In the `Workflow List` tab you can view information about worfklows and their jobs. 
      Some workflows are preinstalled in the platform, others can be installed as :term:`extensions<extension>`.

    workflow-extension
      A workflow extension is an installable Helm chart that contains either one or multiple Airflow :term:`DAGs<dag>` and :term`operators<operator>`. 
      After installing a workflow extension, you can see the DAGs available under Workflow Execution menu.

    application
      In the scope of Kaapana an application is a :term:`service` that can be installed as an :term:`extension<extension>` into a running platform. 
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
      In Kaapana we differntiate between two types of operators:
      
        - :term:`Local operators<local-operator>` run python code in the :term:`container` of the Airflow-Scheduler :term:`service`.
        - :term:`Processing container<processing-container>` spawn dedicated :term:`containers<container>` in the :term:`project`-namespace to execute its code.
    
    local-operator
      A local operator is an Airflow operator that runs python code and is executed in the :term:`container` of the Airflow-Scheduler :term:`service`. 
      Local operators are not scalable, but they are fast to execute and do not require a :term:`container` to run.
    
    processing-container
      A processing-container can refer to two this:
      
      #. A :term:`container` image that is build for data processing.
      #. The runtime of a container image that processes data.

      In Kaapana processing-containers are combined in processing-pipelines that consist of multiple data-processing steps.

    project
      A project is a logical grouping of data, workflows, and other resources within the :term:`kaapana-platform`.
      Projects can be used to separate different use cases or research projects. 
      You can create and manage projects in the :ref:`System > Projects<projects>`.
      Upon creating a project multiple objects are created:
      
      - A dedicated namespace is created in the :term:`Kubernetes<kubernetes>` cluster.
      - In Keycloak a *project-system-user* is created that has access to all data associated with the project. 
        Within any :term:`processing-container` this *project-system-user* can make authenticated requests to data storages such as the PACS, MinIO and OpenSearch.
      - In the :term:`access-information-interface` a project is created and the and the *project-system-user* is mapped to the project role *admin*.
      - In MinIO a dedicated bucket and dedicated access policies are created.
      - In OpenSearch a dedicated index is created together with related roles and role-mappings.

    dicom-web-filter
      The DicomWebFilter enables series-level access control to DICOM data via a DicomWeb API. 
      For example, two users can access the same DICOM study but only specific series within it. 
      This is required in scenarios where a user generates segmentations for certain series of a study and does not want to share these segmentations.
      The DicomWebFilter operates as a database storing access information and a REST API supporting the DicomWeb standard. 
      Acting as an intermediary layer, it filters data received from a PACS based on the client’s access token and stored access rules.
      A management API is also provided for updating access information.

    access-information-interface

      * **Database**: Stores user, project, and permission data.
      * **REST API**: Enables Keycloak token mappers to fetch permissions and manage stored information.

      Main database objects:

      - **Rights**: Key-value claims for access tokens.
      - **Projects**: Projects bundle the information.
      - **Roles**: Collections of rights mapped to users and projects.
      - **UsersProjectsRoles**: Links users, roles, and projects. A user can only have a single UsersProjectsRoles mapping per project. But a user can be mapped to the same role for multiple projects.

      E.g. if a role that contains the right :code:`{"claim_key": "opensearch", "claim_value": "admin_project"}` is mapped to user A in Project foo, the access token of user A will contain the claim :code:`"opensearch": ["admin_project_foo"]`. 
      Opensearch is configured accordingly to look for backend-roles in the opensearch claim of the access token and to know which permissions to grant users with the respective roles.
      Initial rights, roles, projects and respective mappings can be configured in the `access-information-interface-config <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/release/0.5.0/services/data-separation/access-information-interface/access-information-interface-chart/templates/configmap.yaml>`_ . 
      Per default version 0.5.0 comes with only one project role, i.e. :code:`admin`. 
      This role grants access to the project bucket in Minio and the project index in opensearch.

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
      It contains the fundamental features of the platform such as reverse proxy, authentication, and kube-helm backend. It contains :term:`kaapana-platform-chart` as a sub-chart.

    kaapana-platform-chart
      This :term:`Helm<helm>` chart consists of most of the interactive components of Kaapana, such as Airflow, PACS, Minio, landing-page and Kaapana backend.
    
    containerd
      We use `containerd <https://containerd.io/>`_ as runtime environment for the :term:`containers<container>` in the :term:`Kubernetes<kubernetes>` cluster.
      It manages the lifecycle of a container.

    container
      A container is a self contained virtual environment that runs a software along with the code and all of its dependencies.
      In this way, it can run quickly and reliably on any environment.
      We utilize :term:`containerd` to run containers.
      In Kaapana, every :term:`service` runs within a container.
      Containers are specified by container images that are built according to a file e.g. a Dockerfile.
    
    microk8s
      MicoK8s is a lightweight, single-package :term:`Kubernetes<kubernetes>` distribution that we utilize to set up our Kubernetes cluster.

    kubernetes
      Kubernetes is an open-source container-orchestration system that we use to manage all the :term:`containers<container>` required for Kaapana.

    server-installation-script
      This script is used to install all required dependencies on the :term:`server`.
      It can be found within the Kaapana-repository: :code:`./kaapana/server-installation/server_installation.sh`.
      It will execute the following steps:

        #. Configure a proxy (if needed)
        #. Install packages if not present: snap, nano, jq, curl, net-tools, core20, core24, helm
        #. Install, configure and start :term:`microk8s`
        #. Add alias for :code:`kubectl` to :code:`.bashrc` file and enable auto-completion
        #. (opt) Change the SSL-certificates

      Currently supported operating systems are listed in :ref:`requirements`.
    
    deploy-platform-script
      This script is used to deploy a :term:`kaapana-platform` into a :term:`Kubernetes<kubernetes>` cluster or to undeploy a platform. 
      It basically installs the :term:`kaapana-admin-chart` using :term:`Helm<helm>`. 
      After building the platform you can find the script at :code:`kaapana/build/kaapana-admin-chart/deploy_platform.sh`.

    service
      Kaapana services are specific components of the platform that include one or multiple web-server such as an web-API or a web-interface.
      Examples for services are Minio, OHIF, Airflow etc..

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