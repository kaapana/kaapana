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
The role `project-manager` grants full access to the project-managing API of Kaapana.
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