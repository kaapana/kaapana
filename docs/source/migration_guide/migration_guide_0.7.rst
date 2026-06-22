.. _migration_guide_0.7:

Migration from Version 0.6.x to 0.7.x
*************************************

Keycloak: two-client authentication
===================================

From 0.7, platform services authenticate to Keycloak through two dedicated
clients instead of the Keycloak admin password
(see :ref:`service_to_service_auth`):

- ``kaapana-admin`` (master realm) — used only by the setup and bootstrap jobs.
- ``kaapana-service`` (kaapana realm) — used by the runtime services.

Your Keycloak realm, users and groups are preserved; only the way services
authenticate internally changes. No user data is migrated or lost.

On the first 0.7 deployment
---------------------------

The two clients are created automatically by the bootstrap job. To create the
``kaapana-admin`` client it needs your **current** Keycloak admin password
**once**; afterwards every later deployment runs without it.

.. warning::

   **Supply your current admin password through the** ``KEYCLOAK_ADMIN_PASSWORD``
   **environment variable (or** ``--keycloak-admin-password-file`` **) — not the
   interactive prompt.**

   On the first 0.7 deployment the platform cannot tell an upgrade from a fresh
   install, so the interactive prompt validates the password against the new
   policy (at least 8 characters with an upper-case letter, a lower-case letter, a
   digit and a special character) and would **reject** an existing password that
   does not meet it. A value from the environment or a file is used as-is and is
   not validated.

.. code-block:: bash

   export KEYCLOAK_ADMIN_PASSWORD='<your current admin password>'
   ./kaapanactl.sh deploy --chart <KAAPANA_ADMIN_CHART> ...

After the ``kaapana-admin`` client exists, all later deployments run without the
admin password.

.. tip::

   A password passed through an environment variable or on the command line can
   linger in shell history, process listings or CI logs. Once the migration is
   done, change the admin password through the Keycloak UI — from 0.7 this no
   longer disrupts running services (in earlier versions it left them unable to
   authenticate). See :ref:`Keycloak admin password <keycloak_admin_password>`.

Troubleshooting
---------------

- **Bootstrap fails or the kaapana realm is missing:** the ``kaapana-admin``
  client could not be created, usually because the supplied password did not match
  the current Keycloak admin password. Re-run the deployment with the correct
  password.
- **Manual provisioning:** to set the clients up by hand, run
  ``platforms/migrate_keycloak_service_client.sh`` (it requires ``ADMIN_PASSWORD``
  and ``KEYCLOAK_URL``).
