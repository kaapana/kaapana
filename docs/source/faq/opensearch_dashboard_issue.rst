OpenSearch dashboard does not work
**********************************

If you encounter an issue with the OpenSearch dashboard, such as an error message like :code:`Could not locate that index-pattern-field`, it may be due to incomplete meta-data extraction from the images.
You can resolve this by going to :code:`https://<server-domain>/meta`

This is the OpenSearch dashboard. Select "Manage" on the top right menu or "Management" in the menu on the left and then "Index Patterns''. Then you should see an entry called "project-*". Click on it and on the next page there is a refresh button at the top right corner.
By clicking this button the metadata will be updated for the view. Now the dashboard should work as expected.