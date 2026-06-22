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

1. Navigate to Keycloak and log in as the ``admin`` user (see :ref:`Keycloak admin password <keycloak_admin_password>` for how the password is set).
2. In the Keycloak menu navigate to the `Users` tab.
3. Click on `Add user`.
4. Fill in the required fields `Username`, `Email`, `First Name` and `Last Name`.
5. You should join one of the :ref:`keycloak groups <keycloak_groups>` above.
6. Click `Create`
7. Change to the `Credentials` tab of the new user and set a password.

.. note::

   Upon first login any user is automatically added to a default project.
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
This can be done before building the platform by configuring the file :code:`kaapana-realm.json` in the keycloak-setup-chart.
Just remove :code:`first-login-listener` from the list :code:`eventsListeners`.
Alternatively, you can always disable this feature in a running platform in the Keycloak admin console under *Realm settings > Events*.

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

.. _keycloak_admin_password:

Administrative access and credentials
*************************************

Kaapana's Keycloak setup has an **admin account** and two internal **service
clients**:

* The **admin account** — the ``admin`` user of the *master* realm. This is the
  human login for the Keycloak admin console and has full administrative rights.
  It is the credential you use to manage users, groups and clients by hand.
* The **kaapana-admin** and **kaapana-service** clients — credentials the
  platform uses internally, the first to configure Keycloak during deployment
  and the second for runtime user and group lookups. You never log in with
  these; they are kept separate from the admin account and from each other, and
  are described under :ref:`service_to_service_auth`.

As an operator you mainly manage the admin password.

Setting the admin password
--------------------------

On the first deployment with :term:`kaapanactl` the admin password is resolved
from the first available of these sources; later deployments reuse the stored
password and do not ask again, unless the stored credential no longer works:

#. **File** — ``--keycloak-admin-password-file <path>`` reads the password from
   the file at that path (this pairs well with a mounted secret).
#. **Environment variable** — ``KEYCLOAK_ADMIN_PASSWORD`` is taken straight from
   the environment.
#. **Interactive prompt** — if neither of the above is set and a terminal is
   available (not ``--quiet``), you are prompted. Leave the prompt empty to
   generate a random password, or enter your own; an entered password is
   confirmed and must meet the Keycloak policy (at least 8 characters including
   an upper-case letter, a lower-case letter, a digit and a special character).
#. **Generated** — with no file, no environment variable and no terminal
   (``--quiet``, CI/CD), a random password is generated.

The file and the environment variable take precedence over the prompt, so an
exported ``KEYCLOAK_ADMIN_PASSWORD`` is used even on an interactive deploy — you
are not prompted in that case. A password from the file or the environment is
used as-is and, unlike the interactive prompt, is **not** checked against the
password policy, so make sure it meets the requirements yourself. A generated
password is marked temporary, printed once after the deploy, and you are asked to
change it on first login.

Changing the admin password
---------------------------

The admin password can be changed at any time through the *admin* user in the
*master* realm of the Keycloak UI. A password that was generated automatically on
a fresh install is temporary and should be replaced with one of your own.
Changing the admin password has no further effect on the rest of the platform.

Rotating service secrets
------------------------

The ``kaapana-service``, ``system-user`` and OIDC client secrets are regenerated
on every deployment and written into Keycloak by the setup job. The platform
manages them for you — there is no need to rotate or copy them by hand.

Adding your own Keycloak client
*******************************

To integrate your own application, register an additional client in the
``kaapana`` realm. There are two ways:

* **In a running platform** — log in to the Keycloak admin console, select the
  ``kaapana`` realm, and create the client under *Clients > Create client*.
  Choose the OAuth2 flow your application needs and, for a confidential client,
  read its secret from the *Credentials* tab.
* **Persisted across rebuilds** — add a client definition as a JSON file under the
  keycloak-setup chart's realm objects directory
  (``services/kaapana-admin/keycloak/keycloak-setup/keycloak-setup-chart/realm_objects/``)
  and list it in that chart's ``realm-objects-configmap.yaml`` before building the
  platform. The setup job applies it on every deploy. The bundled
  ``kaapana-client.json`` can serve as a template.

To call Kaapana's APIs from your client, see the *Client access to Kaapana APIs*
section on the :ref:`Access Control <access_control_root>` page.