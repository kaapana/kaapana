Kibana dashboard does not work
******************************

You open Kibana/Meta and you see something like this?


.. figure:: ../_static/img/kibana_bug.png
   :align: center
   :scale: 25%

The error occurred, because the dashboard was opened while not all the meta-data of the images were extracted. You can resolve this by going to

::

    https://<server-domain>/meta

this is the Kibana dashboard. Select "Management" on the left hand side and then "Index Patterns''. Then you should see a panel called "meta-index". On the top right corner there
is a refresh button. By clicking this button the meta-data will be updated for the view. Now your dashboard should work as expected!