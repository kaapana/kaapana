.. _send_images_to_the_platform_doc:

Send images to the platform
===========================

Ideally you send pictures directly from a PACS to the platform. The configuration of the PACS within the platform can be found on :ref:`specs_doc`.
If you have DICOMs on your local PC that you would like to send to the platform, we recommend to use *dcmsend* (`installation <https://dicom.offis.de/dcmtk.php.en>`_, `command <https://support.dcmtk.org/docs/dcmsend.html>`_). An example command to send images of a folder *dicoms* to the platform
would be:

::

    dcmsend --call '<your title of the dataset>' -v 10.128.129.41 11112 --scan-directories --scan-pattern *.dcm --recurse ./


