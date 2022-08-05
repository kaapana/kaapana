There seems to be something wrong with the landing-page visualization in the Browser

.. toctree::
    :glob:


Minio is not available because of Error 400
-------------------------------------------

This error usually occurs, when the hostname was set incorrectly in a previous deployment.
Follow these steps to fix this issue:

1. Navigate to Systems>Keycloak in the menu bar
2. Click on Administration Console
3. Insert username and password, by default username=admin and password=Kaapana2020
4. Navigate to the menu point Clients in the Keycloak menu bar
5. Click on kaapana in the column Client ID 
6. In the field Valid Redirect URLs change the domain for the Minio URL
   e.g. change
   :code:`https://my.wrong.domain:443/minio-console/oauth_callback/`
   to :code:`https://my-correct-domain:443/minio-console/oauth_callback/`
7. Scroll down and save the changes
8. Press Ctrl+F5 to refresh the page and the cache

