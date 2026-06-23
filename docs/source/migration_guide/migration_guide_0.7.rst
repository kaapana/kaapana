.. _migration_guide_0.7:

Migration from Version 0.6.x to 0.7.x
*************************************

Keycloak: two-client authentication
===================================

From 0.7, platform services authenticate to Keycloak through two dedicated
clients instead of the Keycloak admin password
(see :ref:`service_to_service_auth`):

- ``kaapana-admin`` (master realm) - used only by the setup and bootstrap jobs.
- ``kaapana-service`` (kaapana realm) - used by the runtime services.

Your Keycloak realm, users and groups are preserved; only the way services
authenticate internally changes. No user data is migrated or lost.

On the first 0.7 deployment
---------------------------

The two clients are created automatically by the bootstrap job. To create the
``kaapana-admin`` client it needs your **current** Keycloak admin password
**once**; afterwards every later deployment runs without it.

Run the migration deployment with ``--set-keycloak-admin-password`` and enter
your current admin password at the prompt:

.. code-block:: bash

   ./kaapanactl.sh deploy --set-keycloak-admin-password --chart <KAAPANA_ADMIN_CHART> ...

The entered password is used as-is and is not validated, so an existing password
that does not meet the new policy is still accepted.

.. warning::

   Do not run the migration deployment *without* ``--set-keycloak-admin-password``.
   A plain deployment generates a new random password and hands it to the
   bootstrap, which then cannot authenticate against your existing Keycloak and
   fails.

After the ``kaapana-admin`` client exists, all later deployments run without the
admin password.

.. tip::

   From 0.7 the admin password can be changed through the Keycloak UI or with
   ``./kaapanactl.sh set-keycloak-admin-password`` without disrupting running
   services (in earlier versions it left them unable to authenticate). See
   :ref:`Keycloak admin password <keycloak_admin_password>`.

Troubleshooting
---------------

- **Bootstrap fails or the kaapana realm is missing:** the ``kaapana-admin``
  client could not be created, usually because the entered password did not match
  the current Keycloak admin password. Re-run the deployment with
  ``--set-keycloak-admin-password`` and enter the correct password.
- **Manual provisioning:** to set the clients up by hand, run
  ``platforms/migrate_keycloak_service_client.sh`` (it requires ``ADMIN_PASSWORD``
  and ``KEYCLOAK_URL``).
