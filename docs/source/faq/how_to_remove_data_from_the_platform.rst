How to remove data from the platform
************************************

There are several ways of removing data from the platform depending on the kind of data you want to remove.
In general we distinguish between DICOM data and non-DICOM data.
All DICOM data is stored in an internal PACS and the metadata in Elasticsearch.
Non-DICOM data is stored in Minio buckets.

Removing DICOM data 
-------------------

DICOM data can be removed by triggering the :code:`delete-series-from-platform` workflow in the Meta-Dashboard.
For information about how to use the Meta-Dashboard to select data and trigger a workflow take a look at the :ref:`Meta-Dashboard tutorial<TODO>` **TODO: Add reference link**.

.. hint:: 
    The :code:`delete-series-from-platform` workflow can also be triggered in the other dashboards i.e. *Segmentations* and *Trained Models*.

The :code:`delete-series-from-platform` workflow deletes all series selected in the Meta-Dashboard from the PACS 
and additionally deletes all corresponding metadata from Elasticsearch.

In case you want to delete a lot of data you can set :code:`Delete entire study: True` in the workflow dialog,
which will be much faster.
With this setting the entire study of each selected series will be deleted.
This is also handy, if you want to delete a series and automatically all of the available segmentations.

.. note:: 
    The hierarchy of DICOM data is:
    Collection > Patient > Study > Series > Images.
    Hence, deleting the entire study of a series might include additional series which are not selected in the dashboard.

Removing data from MINIO
------------------------
Non-DICOM data is stored in Minio buckets.
You find Minio in the menu under the tab-index "Store".
Here you see a list of all available buckets.
Click on the "Browse->" button of a bucket to browse through the data inside it.
Now you can select and delete data.
