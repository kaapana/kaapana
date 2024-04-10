.. _keycloak:

Keycloak
^^^^^^^^^^

Keycloak is an open source identity and access management solution that we integrated in our platform for identity and access management. 
It can be accessed via *System* tab in the web interface.

Access to features of the platform is separated into two groups:

* Members of the **kaapana_admin** group have unlimited access to all features of the platform.
* Members of the **kaapana_user** group have access to the all features of the `Workflows Management System` without the `Instance Overview`. Furhtermore, they have limited access to the `PACS` and `MinIO`. They have full access to `Meta`.


How to create a new user
*************************

1. Navigate to Keycloak and login with the Keycloak credentials (Default: admin - Kaapana2020)
2. In the Keycloak menu navigate to the `Users` tab.
3. Click on `Add user`.
4. Fill in the required fields `Username` and `Email`.
5. If you want to create an admin user join `kaapana_admin`. For a non-admin user join the `kaapana_user` group.
6. Click `Create`
7. Change to the `Credentials` tab of the new user and set a password.


Any user in the `kaapana_admin` group has unrestricted access to all features of the platform.
Users in the `kaapana_user` group have only limited access.
I.e. they have only access 


Authorization
***************

Traefik routes each request through a authorization middleware.
This middleware forwards each request to a authorization server.
The authorization server asks the Policy Decision Point (DPD), if the user has sufficient permissions to make the request.
We deploy `Open Policy Agent (OPA) <https://www.openpolicyagent.org/docs/latest/http-api-authorization/>`_ as DPD.


Connecting an Active Directory
********************************

In order to connect to an active directory go to the tap **User Federation**. 
Depending on your needs select *ldap* or *kerberos*. 
The necessary configuration you should be able to get from your institution. 
If everything is configured correctly you are able to login with the credentials from the Active Directory.