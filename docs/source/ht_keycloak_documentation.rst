.. _keycloak_documentation:

Keycloak: Add users to the platform
===================================

Keycloak is an open source Identity and Access Management solution that we integrated in our platform to manage authentication and different user roles. 
You can access keycloak via the dashboard (only if you have admin rights) or directly via */auth/*.

The default credentials to access the Admin section of Keycloak are:

-  Admin username: "jipadmin"
-  Admin password: "DKjipTK"

As it does not make any sense to repeat the original `documentation of keycloak <https://www.keycloak.org/documentation.html>`_ we only present here some simple steps.

Add user to your platform
-------------------------

Depending on your needs you can add users manually or connect Keycloak instance i.e. to an Active Directory.

Adding a user manually
^^^^^^^^^^^^^^^^^^^^^^

Once you are logged in you can add users in the section **Users**. By selecting a user you can change i.e. his password in the tab **Credentials** or 
change his role under **Role mappings**. Try i.e. to add a user who has no admin rights, only user rights. Currently there are only two user roles. The 
**admin** has some more privileges than a normal **user**, i.e. a **user** can not access the Kubernetes dashboard and can not see all components on the
landing page.

Connecting with an Active Directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to connect to an active direcotry go to the tap **User Federation**. Depending on your needs select *ldap* or *kerberos*. The necessary configuration you should be able to get from your institution. 
If everything is configured correctly you should be able to login with your credentials form the Active Directory.
