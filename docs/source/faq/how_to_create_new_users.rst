.. _how_to_create_new_users:

How to create new users
*************************

User management is currently only possible via Keycloak.
In order to create a new user navigate to Keycloak and login with the Keycloak credentials (Default: admin - Kaapana2020).
Change the realm to "kaapana" and in the Keycloak menu navigate to "Users".
Then follow the steps below to either create an admin or a non-admin user.


How to create a new admin user
------------------------------

To create a new admin user, follow these steps:

1. Create a new user and add them to the `all_data` group.
2. Provide the user with an email address. Note that this is a required field.
3. Assign the necessary credentials to the user.
4. Grant the user the `policy: consoleAdmin` attribute.

How to create a non-admin User
------------------------------

To create a non-admin user, follow these steps:

1. Create a new user, ensuring they are **not** added to the `all_data` group.
2. Provide the user with an email address. Note that this is a required field.
3. Assign the `user` role to the new user.
4. Grant the user the `policy: consoleAdmin` attribute.

Non-admin users don't have access to the "System" endpoints and the Meta-Dashboards.