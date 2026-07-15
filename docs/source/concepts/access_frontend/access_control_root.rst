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

Every web request to Kaapana is subject to authorization checks that determine whether access to a resource is permitted, based on the access token included with the request and a set of configurable policies, evaluated as Rego policies at the **Policy Decision Point (PDP)** -- an instance of **Open Policy Agent (OPA)**.
See :ref:`concepts_authorization_flow` for the full request chain (Keycloak, Traefik, the Auth Backend and OPA) that produces this decision; the rest of this page is about *what* can be controlled, not how a request gets authorized.

.. _two_levels_of_roles:

Two Levels of Roles
^^^^^^^^^^^^^^^^^^^^

Kaapana has two role types:

* **Realm roles** -- ``user``, ``project-manager``, ``admin``. Global, assigned via :ref:`Keycloak group membership<keycloak_groups>`. ``user`` is the default role for every account. ``admin`` grants unrestricted access to all projects and platform features. ``project-manager`` grants access to the project-managing API (``System > Projects``); rarely assigned without ``admin``.
* **Project roles** -- ``scientist``, ``principal-investigator`` by default. Assigned per project: a user can hold a different project role in each project. Each project role maps to a fixed set of :ref:`AII rights<aii>`.

A realm role determines which projects and platform areas a user can reach. A project role determines what a user can do inside a project they have access to. ``admin`` bypasses project-role checks (see note below).

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

.. _aii:

Access Information Interface (AII)
**********************************

See :ref:`concepts_architecture` for the AII's tech stack and how it fits alongside Kaapana's other custom services; this section is about what it manages.

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


Client access to Kaapana APIs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every API in Kaapana is also reachable from an external client, project-scoped the same way as everything else on this page.
See :ref:`concepts_programmatic_access` for how to authenticate and call the APIs with ``KaapanaApiService``.


.. _service_to_service_auth:

Service-to-service authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Besides authenticating end users, Kaapana authenticates against Keycloak on its
own behalf, for two distinct purposes:

* **Administering Keycloak** - the setup and bootstrap jobs create and configure
  the realm, its clients, groups and users.
* **Runtime lookups** - services such as ``kaapana-backend`` and the
  :term:`AII<access-information-interface>` read and manage users and groups
  while the platform is running.

These purposes require very different privilege levels, so Kaapana uses two
separate Keycloak clients instead of one shared credential:

.. list-table::
   :header-rows: 1
   :widths: 20 15 35 30

   * - Client
     - Realm
     - Roles
     - Used by
   * - ``kaapana-admin``
     - ``master``
     - master ``admin`` role
     - the setup and bootstrap jobs (admin namespace)
   * - ``kaapana-service``
     - ``kaapana``
     - ``manage-users``, ``query-users``, ``query-groups``, ``view-realm``
     - runtime services (``kaapana-backend``, the :term:`AII<access-information-interface>`, project-namespace)

Both clients authenticate via the OAuth2 ``client_credentials`` grant. The
``kaapana-admin`` secret is mounted only into the setup and bootstrap jobs, not
into runtime pods. It is the only persisted credential; the ``kaapana-service``,
OIDC and ``system-user`` secrets are regenerated on every deploy.

Bootstrap and setup jobs
************************

Two jobs provision and configure Keycloak on every deploy.

**Bootstrap job** (``keycloak-bootstrap-chart``) establishes the ``kaapana-admin``
client and applies the admin password. It runs on every deploy.

*What it expects:*

* the ``kaapana-admin`` client secret, from the ``kaapana-admin-password`` secret
  in the admin namespace;
* the admin password to apply, supplied by the deploy (a random one, or the value
  entered with ``--set-keycloak-admin-password``), and whether that password is
  temporary.

*What it does:*

* If the ``kaapana-admin`` client already authenticates, the job authenticates
  through the client - no admin password is required - and resets the master-realm
  admin password to the supplied value. This is the normal path on every redeploy.
* If the client is missing or its secret no longer works, the job authenticates
  with the supplied admin password, (re)creates the client, grants it the master
  ``admin`` role, and then applies the password. This is the path on a fresh
  install and on the first 0.7 deploy of an upgraded installation.

*What it guarantees after a successful run:*

* the ``kaapana-admin`` client exists in the *master* realm with full admin
  rights, so the setup job and every later deploy authenticate through it;
* the master-realm admin password equals the value the deploy supplied;
* the admin password never reaches the setup job or any runtime pod.

*Warnings and errors:*

* *No admin password supplied, but the client works* - the job ran without a
  password (for example when started by hand). The connection is fine, but the
  password was not (re)set. A normal deploy always supplies one.
* *Client not functional and no admin password supplied* - the client does not
  exist yet and no password was given, so the job cannot bootstrap. Re-run the
  deploy with ``--set-keycloak-admin-password`` and provide the current admin
  password (on an upgrade, your existing one).
* *Admin authentication failed* - the client is missing and the supplied password
  does not match the current Keycloak admin password. Re-run with the correct one.
* *Could not create the client* / *applying the admin password failed* -
  authentication succeeded but provisioning did not. Check the Keycloak server
  logs and the admin user's permissions.

**Setup job** (``keycloak-setup-chart``) authenticates as the ``kaapana-admin``
client and applies the full realm configuration. It also writes the rotating
secrets (OIDC, ``kaapana-service``, ``system-user``) into Keycloak on every
deploy, keeping the Kubernetes secrets and Keycloak in sync.