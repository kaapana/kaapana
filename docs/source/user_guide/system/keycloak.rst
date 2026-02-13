.. _keycloak:

Keycloak
^^^^^^^^^^

Keycloak is an open source identity and access management solution that we integrated in our platform for identity and access management. 
It can be accessed via *System* tab in the web interface.

.. _keycloak_groups:

Kaapana user groups
*********************
Access to platform features is segmented into three user groups:


**kaapana_user**:
Members of this group inherit the `user` role. 
The role `user` grants access to all features within the `Workflows Management System` except for the `Instance Overview`. 
Additionally, their access to `OpenSeach` and `MinIO` is limited to project specific data.

**kaapana_project_manager**: 
Members of this group inherit the `project-manager` and `user` roles. 
The role `project-manager` grants full access to the :term:`project`-managing API of Kaapana.
Users with this role can use all functionalities under :ref:`System>Projects <projects>`.

**kaapana_admin**: 
Members of this group inherit the roles `user`, `project-manager` and `admin`.
The `admin` role grants unrestricted access to all platform features and all projects.

.. _how_to_create_a_user:

How to create a new user
*************************

1. Navigate to Keycloak and login with the Keycloak credentials (Default: admin - Kaapana2020)
2. In the Keycloak menu navigate to the `Users` tab.
3. Click on `Add user`.
4. Fill in the required fields `Username`, `Email`, `First Name` and `Last Name`.
5. You should join one of the :ref:`keycloak groups <keycloak_groups>` above.
6. Click `Create`
7. Change to the `Credentials` tab of the new user and set a password.

.. note::

   Any user created via the Keycloak admin console will automatically be added to a public project.
   The default name of this project is *public* and the default role is set to *scientist*.
   This behavior is :ref:`configurable <configure_default_proejct>`.

.. _configure_default_proejct:

Configuration of the default project
--------------------------------------

Project name and project role are configured in the configmap :code:`defaultProject.yaml` in the Keycloak helm-chart.
You can either adjust :code:`config.json` inside this configmap before deploying the platform or 
in a running platform by changing the configmap :code:`default-project-role-user-mapping` via the Kubernetes Dashboard.
If you do the latter you have to delete the Keycloak pod for your changes to become active.

Either way, the corresponding project and the role have to exist in the platform.
You can define a list of initial projects and roles that will be created during platform deployment in :code:`configmap.yaml` in the access-information-interface-chart.

You can also fully disable this feature.
This can be done before building the platform by configuring the file :code:`kaapana-realm.json` in the keycloak-init-chart.
Just remove :code:`user-created-http-listener` and :code:`first-login-listener` from the list :code:`eventsListeners`.
Alternatively, you can always disable this feature in a running platform in the Keycloak admin console under *Realm settings > Events*.

The events listener :code:`user-created-http-listener` will map any user that was created via the admin console to the default project.
The events listener :code:`first-login-listener` will map any user during its first login to the default project.

Authorization
***************

Traefik directs every request through an authorization middleware, which in turn forwards the request to an authorization server. 
This server consults the Policy Decision Point (PDP) to determine whether the user has the requisite permissions for the request. 
For our Policy Decision Point (PDP), we deploy `Open Policy Agent (OPA) <https://www.openpolicyagent.org/docs/latest/http-api-authorization/>`_.


Connecting an Active Directory
********************************

In order to connect to an active directory go to the tap **User Federation**. 
Depending on your needs select *ldap* or *kerberos*. 
The necessary configuration you should be able to get from your institution. 
If everything is configured correctly you are able to login with the credentials from the Active Directory.