OpenSearch dashboard does not work
**********************************

You open OpenSearch/Meta and you see something like this?


.. figure:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/img/kibana_bug.png
   :align: center

The error occurred, because the dashboard was opened while not all the meta-data of the images were extracted. You can resolve this by going to

::

    https://<server-domain>/meta

this is the OpenSearch dashboard. Select "Manage" on the top right menu or "Stack Management" in the menu on the left and then "Index Patterns''. Then you should see an entry called "meta-index". Click on it and on the next page there is a refresh button at the top right corner.
By clicking this button the meta-data will be updated for the view. Now your dashboard should work as expected!