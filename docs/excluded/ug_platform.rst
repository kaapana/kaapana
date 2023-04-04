.. _user_guide_platform_doc:

User Guide Platform
===================

| If the platform has been successfully installed, you can start here to get familiar with the basic principles.

When the system gets initialized, the platform sends a first image to the dicom receiver to check its function.
If you select the 'Meta' tab on the main page, you should see that there is already an image listed. 

.. figure:: _static/img/meta_beginning.png
   :align: center
   :scale: 18%

The system is configured to display the metadata of all images in this example dashboard.

To add more, you need to send images from your pacs to the platform.

.. note::

  The server provides a dicom receiver on the port 11112. 

If you haven't already registered the server within you clinic pacs, you should follow the guide: :ref:`specs_doc`
After this, you can send the first image to the server from within your default pacs interface.
You can check this by viewing the currently running workflows in the Airflow area.

.. figure:: _static/img/airflow_start.png
   :align: center
   :scale: 18%

.. raw:: latex

    \clearpage

Bright green (dark green --> completed, red --> error ) cirlces indicate a running workflow. In the case of the metadata-extraction 
this happens quite quickly. It may already be completed when you look for it.

.. figure:: _static/img/airflow_meta.png
   :align: center
   :scale: 40%

The metadata will appear in the 'DKTK Kaapana' dashboard of the Meta section of the platform.
You should now see two (or more) entries in the list. 
The 'Datasets' visualization will show the AE-title, the image was sent to (Kaapana when you used the default).

.. figure:: _static/img/meta_second_image.png
   :align: center
   :scale: 18%


This is the standard procedure for sending images to the platform. 
It is also possible to trigger any workflow automatically (e.g. selected by special dicom tags).

Manual Workflow Triggering
--------------------------



You can also select a dataset within the 'Meta' dashboard and trigger a workflow.
Every visualisation within Meta dashboard can be used to set filter based on the entries.
If you hover over the corresponding entry, two magnifying glasses should appear (+ and -).
If you click on the '+' the data will be filtered for data with the same tag content.
If you select the '-', data with this condition will be excuded.

You can also simply click on a modality in the 'Modality Donut' to reduce all data to that modality.

|pic1| |pic2|

.. |pic1| image:: _static/img/meta_filtering.png
   :width: 50%

.. |pic2| image:: _static/img/meta_modality.png
   :width: 40%

.. raw:: latex

    \clearpage


You can also create manual filters by clicking on 'Add a filter' at the top of the dashboard and specifying the desired properties.

.. figure:: _static/img/meta_filter.png
   :align: center
   :scale: 30%


Once you have selected your dataset, you can choose and start a workflow in the lower part of the dashboard.

.. figure:: _static/img/dag_tigger.png
   :align: center
   :scale: 30%


The current implementation is more a proof of concept than the finished system.

We will offer a seperate experiment management in the future.

Go to the next section  to get an overview of the :ref:`workflows <workflow start>` that are integrated so far. Following the :ref:`Development guide <dev_guide_doc>` you will be able to write your own workflows!

.. raw:: latex

    \clearpage