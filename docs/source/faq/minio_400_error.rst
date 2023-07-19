MinIO not available due to Error 400
-------------------------------------------

This error usually occurs, when the hostname was set incorrectly in a previous deployment.
Follow these steps to fix this issue:

1. In the menu navigate to `Systems` and `Keycloak`.
2. Click on `Administration Console` and login (default credentials - admin:Kaapana2020).
3. Navigate to the menu point `Clients` in the Keycloak menu bar.
4. In the Keycloak menu change the realm from `master` to `kaapana`.
5. Under the point `Manage` click on `Clients` and in the column `Client ID` click on `kaapana`.
6. Make sure you are in the tab `Settings`. In the field `Valid Redirect URLs` change the domain for the Minio URL.
   e.g. change
   :code:`https://my.wrong.domain:443/minio-console/oauth_callback/`
   to :code:`https://my-correct-domain:443/minio-console/oauth_callback/`
7. Save the changes.
8. Go back to the MinIO page and press Ctrl+F5 to refresh the page and the cache