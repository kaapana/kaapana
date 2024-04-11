.. _keycloak:

Keycloak
^^^^^^^^^^

Keycloak is an open source identity and access management solution that we integrated in our platform for identity and access management. 
It can be accessed via *System* tab in the web interface.

Access to platform features is segmented into two groups:

* **kaapana_admin**: Members of this group inherit the `admin` role and the MinIO policy `consoleAdmin`. They have unrestricted access to all platform features.
* **kaapana_user**: Members of this group inherit the `user` role and the MinIO policy `kaapanaUser`. They can access all features within the `Workflows Management System` except for the `Instance Overview`. Additionally, their access to `PACS` and `MinIO` is limited, while they retain full access to `Meta`.

.. _how_to_create_a_user:

How to create a new user
*************************

1. Navigate to Keycloak and login with the Keycloak credentials (Default: admin - Kaapana2020)
2. In the Keycloak menu navigate to the `Users` tab.
3. Click on `Add user`.
4. Fill in the required fields `Username` and `Email`.
5. If you want to create an admin user join `kaapana_admin`. For a non-admin user join the `kaapana_user` group.
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