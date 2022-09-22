.. _delete_images_doc:

Delete images from the platform
===============================

Information of the images is saved in the PACS and in OpenSearch. Starting from Release 1.1 a workflow called 
"delete-series-from-platform" is provided. Simply go to the Meta Dashboard. Select the images you want to delete and start the workflow.
On the Airflow dashboard you can see when the DAG "delete-series-from-platform" has finished, then all your selected images should be deleted
form the platform. For more information check out the documentation of the workflow at :ref:`workflow delete`.