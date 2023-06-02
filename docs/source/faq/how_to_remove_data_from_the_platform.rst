.. _faq_howto_remove_data:

How to remove data from the platform
************************************

There are several ways of removing data from the platform depending on the kind of data you want to remove.
In general we distinguish between DICOM data and non-DICOM data.
All DICOM data is stored in an internal PACS and the metadata in OpenSearch.
Non-DICOM data is stored in Minio buckets.

Removing DICOM data 
-------------------

DICOM data can be removed by triggering the :code:`delete-series-from-platform` workflow in the :ref:`Workflow Management System<wms start>` or the `Datasets` tool.

The :code:`delete-series-from-platform` workflow deletes all series in the :term:`dataset` from the PACS and additionally deletes all corresponding metadata from OpenSearch.
However, it is important to note that the corresponding series identifier will remain within any dataset it is associated with and will not be removed.

In case you want to delete a lot of data you can set :code:`Delete entire study: True` in the workflow dialog, which will be much faster.
With this setting the entire study of each selected series will be deleted.
This is also handy, if you want to delete a series and additionally all of its segmentations.

.. warning:: 
    The hierarchy of DICOM data is:
    Collection > Patient > Study > Series > Images.
    Hence, deleting the entire study of a series might include additional series which are not part of the selected dataset.

Removing data from MINIO
------------------------
Non-DICOM data is stored in Minio buckets.
You find Minio in the menu under the tab-index "Store".
Here you see a list of all available buckets.
Click on the "Browse->" button of a bucket to browse through the data inside it.
Now you can select and delete data.
