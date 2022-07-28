How to send images to the platform
===================================
The current predominate image format of the platform is DICOM. Therefore this section describes how to get DICOM files.
The kaapana platform has several services allowing receive and process DICOM files.
*Different helper scripts to upload files can be found in the `kaapana/utils` folder.*
 
DICOM storage SCU (dcmsend)
----------------------------------
The easiest way to send data to the platform is to use `dcmsend  <https://support.dcmtk.org/docs/dcmsend.html>`_.
The default port is 11112. 
This port can be changed in the during installation:
:code:`/platforms/kaapana-platform/platform-deployment` by changing the DICOM_PORT.

::

   dcmsend -v <ip-address of server> 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>



Web upload
-----------------------------------
On your local PC:

#. create a folder called "dicoms"
#. zip all folders with dicom files
#. put all zipped folders in the folder named "dicoms"

In the Minio UI:

#. Select the bucket *uploads*
#. Upload folder
#. Select your "dicoms" folder
#. Wait until the files are processed by airflow

Put a zipped dicom folder in the Minio bucket *uploads*