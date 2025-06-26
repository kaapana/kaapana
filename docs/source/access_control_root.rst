.. _access_control_root:

Access Control
###############

Kaapana contains strong authorization features that allow to control access to the following resources:

* Data
    * DICOM Data stored in PACS
    * Files stored in MinIO
    * Metadata stored in OpenSearch
* Objects
    * Workflows
    * Jobs 
    * Datasets 
    * Projects
* Services
    * APIs
        * Workflow Management System
        * Extensions API
        * Project API
    * Web Interfaces
        * Airflow
        * Kubernetes Dashboard
        * Keykloak
        * Traefik
        * Prometheus and Grafana
        * Extensions page
* Access to active applications
* Workflow execution


How Access Control Works
^^^^^^^^^^^^^^^^^^^^^^^^

Every web request to Kaapana is subject to authorization checks that determine whether access to a resource is permitted. 
The authorization decision is based on:

* The access token included with the request
* Configurable policies that define the access rules

Authorization decisions are evaluated at the **Policy Decision Point (PDP)**, which is an instance of an **Open Policy Agent (OPA)**. 
Access policies are written using the Rego policy language.

.. _global_system_groups:

Global System Groups
^^^^^^^^^^^^^^^^^^^^

System-wide permissions in Kaapana are managed centrally through groups in :ref:`Keycloak<keycloak>`, the identity and access management system.
For more information about the available system groups and detailed instructions on how to add users to groups, refer to the corresponding section in the :ref:`User Guide <keycloak_groups>`.


Project Rights and Claims
^^^^^^^^^^^^^^^^^^^^^^^^^

Most resources in Kaapana are organized within the scope of a project, which serves as the central unit for managing access to these resources.

In addition to configurable access policies, Kaapana allows the definition of custom rights, providing fine-grained control over project-specific resources. 
These rights are reflected as claims in the user's access token, enabling external services to enforce access restrictions based on project membership and assigned permissions.

Custom rights can be used to control access to services such as:

* MinIO
* OpenSearch
* DICOMWeb API

This mechanism ensures consistent, project-aware access control.

Custom rights can be created in the `confimap <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/0.5.0/services/data-separation/access-information-interface/access-information-interface-chart/templates/configmap.yaml?ref_type=tags>`_ 
of the :term:`Access Information Interface (AII)<access-information-interface>` before the platform is build.

Access Information Interface (AII)
**********************************

The AII provides a REST API for managing:

* **Rights:** Fine-grained permissions associated with specific actions or resources
* **Roles:** Collections of rights that define permission levels
* **Projects:** Bundle of resources and services.
* **User-Project-Role Mappings:** Assignments that link users to specific roles within projects

During authentication, **Keycloak** queries the AII to determine a user's rights. 
For each right granted to the user (based on their project-specific roles), Keycloak populates the user's access token with the corresponding claim.
User-Project-Role mappings can be managed via the :ref:`Project Management Interface<projects>`.

This mechanism enables precise, project-specific authorization. 
It allows you to define different permission levels for users on resources associated with projects, such as:

* Read-only access to datasets
* Permission to submit workflows for specific DAGs
* Administrative control over project resources


Authorization flow
^^^^^^^^^^^^^^^^^^

The following sequence diagram gives a simplified overview of the authorization flow for web requests.

.. mermaid::
    
    sequenceDiagram
        participant C as Client
        participant R as reverse-proxy
        participant K as Keycloak
        participant P as PDP
        participant I as AII

        C->>R: Web request
        K->>I: Request rights
        I-->>K: Return rights
        K-->>R: Return access token
        R->>P: Forward request for authorization
        P-->>R: Return authorization decision
        alt Authorized
            Note right of R: If authorized, forward<br/> request to Kubernetes
            R-->>C: Relay response <br/> from Kubernetes service
        else Unauthorized
            R-->>C: Relay 403
        end


Access Control Within Processing-Containers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:term:`Processing-containers<processing-container>` are tightly coupled to a **task-run** in Airflow, and thus, to a **DAG-run**.  
Since every DAG-run belongs to a specific project, processing-containers always operate within a well-defined **project context**.

Processes running inside these containers often require access to storage services such as:

- **DICOMWeb**  
- **MinIO**  
- **OpenSearch**  

To ensure strict project-based isolation, processes must only be able to access storage resources belonging to the project associated with their DAG-run.

This is enforced through the following mechanisms:

- Processing-containers are executed within dedicated **Kubernetes namespaces**, one per project.
- For each project, a **system user** is created with permissions strictly limited to that project's resources.
- Processing-containers use the credentials of the corresponding project system user to authenticate against the storage services.

This design guarantees that processes inside containers can only interact with storage resources belonging to their project, preventing cross-project data access.

Workflow Execution And Active Applications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The Project Management UI allows to manage, which DAG can be executed as a Workflow by which Project.
* This can be managed by creating or deleting porject-software mappings.
* A default list of project-software-mappings can be configured before building your custom platform at <link>


* Active Applications are also bound to a project-context
* As active applications are spawned in the extension page, the selected project determines the project for which the application will be deployed.
* Applications that are started by workflows like MITK-flow are automatically associated with the project of corresponding workflow.


Workflow Execution and Active Applications  
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The **Project Management UI** provides fine-grained control over which :term:`DAGs<dag>` can be executed as workflows within specific projects. 
This is achieved by managing **project-software mappings**, which define the association between a project and the workflows available to it. 
These mappings can be created or removed as needed to control workflow availability.
Additionally, a default set of project-software mappings can be defined prior to building your custom Kaapana platform in the correpsonding `configuration file <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/0.5.0/services/data-separation/access-information-interface/access-information-interface-chart/templates/configmap.yaml?ref_type=tags>`_ 

Similarly, :term:`active applications<application>` are always tied to a specific **project context**. 
When launching an application via the :ref:`Extension Page<extensions>`, the currently selected project determines the project within which the application will be deployed. 
For applications started automatically by workflows, such as those initiated by **MITK-Flow**, the project association is inherited from the project of the corresponding workflow execution.

This mechanism ensures that both workflow execution and application deployment in Kaapana remain strictly project-bound, maintaining clear separation and secure access to project resources.

.. note::
    Only users within dedicated :ref:`global system groups<global_system_groups>` are able to manage project-software-mappings and to start applications.
    Check out the :ref:`Keycloak user guide<keycloak>` for more information.