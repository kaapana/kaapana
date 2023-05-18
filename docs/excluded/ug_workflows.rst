.. _workflow start:

Workflows
=========

.. _workflow organseg:

Automatic organ segmentation
----------------------------
| **Method:** "3D Statistical Shape Models Incorporating Landmark-Wise Random Regression Forests for Omni-Directional Landmark Detection"
| **Authors:**  Tobias Norajitra and Klaus H. Maier-Hein
| **DOI:** `10.1109/TMI.2016.2600502 <https://ieeexplore.ieee.org/document/7544533>`_

| **What's going on?**
| 1) DICOM will be converted to .nrrd files
| 2) Normalization of input images
| 3) Parallel segmentation of liver,spleen and kindeys (left and right)
| 4) .nrrd segmentations will be converted to DICOM Segmentation (DICOM SEG) object.
| 5) DICOM SEGs will be sent to the internal platform PACS 
| 6) DICOM SEGs will also trigger the :ref:`workflow extractmetadata` workflow
| 7) DICOM SEGs will also be used to trigger the :ref:`workflow radiomics` workflow for feature extraction 

| **Input data:**  
| Filter for **abdominal CT** scans within the meta dashboard. 
|
| **Start processsing:**
| Select  *organ-segmentation* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*


.. _workflow radiomics:

Radiomics
---------
**TBA**

| **What's going on?**
| 1) Selected DICOM SEGs are converted not .nrrd files
| 2) Corresponding CT file is downloaded form the PACS
| 3) Downloaded CT files are converted to \*.nrrd
| 4) Radiomics is done on selected DICOMs
| 5) Extracted radiomics data are pushed to the bucket *radiomics* in Minio and can be downloaded there

| **Input data:**  
| DICOM Segmentations 
|
| **Start processsing:**
| Ideally the dag is triggered within the organ-segmentation workflow. In case you want to manually trigger the dag,
| select  *radiomics* + *BACTH FILE PROCESSING* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*

.. _workflow collect:

Collect metadata
----------------
| **What's going on?**
| 1) DICOMs are annoymized by removing a list of personal tags
| 2) Meta data of the DICOMs are extracted and written to JSON files
| 3) JSON files are concatenated to one JSON file.
| 4) JSON file is zipped and send with a timestamp to the bucket *download* in Minio, where the file can be downloaded

| **Input data:**
| DICOMs
|
| **Start processsing:**
| Select  *collect-metadata*  + *BACTH FILE PROCESSING* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*

.. _workflow delete:

Delete images (dcm)
-------------------
| **What's going on?**
| 1) DICOMsare deleted from the PACS.
| 2) Meta data of DICOMs are deleted from the OpenSearch database.

| **Input data:**
| Filter for DICOMs that you want to remove from the platform. Since in the current verison the files are copied to the local SSD drive, please, do not select too many images at once. 
|
| **Start processsing:**
| Select  *delete-dcm-from-platform* + *BATCH FILE PROCESSING* and click *SEND x RESULTS*

| **Attention**
| In case, you want to resend the images to the server you need to restart the CTP Pod in Kubernetes. In order to this go to Kubernetes, select Namespace "flow", click on "Pods" select the pod named "ctp-..." and then delete the pod by clicking on the trash can on the upper right.

.. _workflow reindex:

Re-index dicoms
---------------
| **What's going on?**
| 1) All meta data saved in OpenSearch are deleted
| 2) For every DICOM within the PACs the dag service-extract-metadata is triggered to write the meta data back to OpenSearch 
 
**Input data:**  
| None
|
| **Start processsing:**
| Trigger the *reindex-pacs* dag manually in Airflow

.. _workflow download:

Download selected files
-----------------------
| **What's going on?**
| 1) DICOMs are zipped and send with a timestamp to the bucket *download* in Minio, where the file can be downloaded

| **Input data:**  
| DICOMs
|
| **Start processsing:**
| Select  *download-selected-files* + *BACTH FILE PROCESSING* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*

.. _workflow extractmetadata:

Extract metadata
-----------------
| **What's going on?**
| 1) Meta data of the DICOM are extracted and written to a JSON file
| 2) The meta data in the JSON file are sent to OpenSearch

| **Input data:**  
| DICOMs
|
| **Start processsing:**
| Select  *service-extract-metadata* + *BACTH FILE PROCESSING* or *SINGLE FILE PRCIESSING* and click *SEND x RESULTS*

.. _workflow incomingdcm:

Process incoming dicom
----------------------
| **What's going on?**
| 1) DICOMs sent to the server are saved in the /dcmdata directory and then copied to the local workflow data folder.
| 2) The dag service-extract-metadata is triggered

| **Input data:**  
| None
|
| **Start processsing:**
| Dag is triggered automatically, once DICOM objects are sent to the server. It should not be triggered manually or with the OpenSearch dashboard

.. _workflow incomingopensearch:

Process incoming OpenSearch
------------------------------
| **What's going on?**
| 1) Downloads the selected DICOMs to the local workflow data folder and triggers the selected dag

| **Input data:**  
| None
|
| **Start processsing:**
| This dag is triggered any time a workflow is started via the OpenSearch dashboard





