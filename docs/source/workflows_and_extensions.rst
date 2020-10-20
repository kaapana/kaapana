.. _workflows_and_extensions start:

List of workflows and extensions
================================

Workflows
^^^^^^^^^

.. _workflows_and_extensions organseg:

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
| 6) DICOM SEGs will also trigger the :ref:`workflows_and_extensions extractmetadata` workflow
| 7) DICOM SEGs will also be used to trigger the :ref:`workflows_and_extensions radiomics` workflow for feature extraction 

| **Input data:**  
| Filter for **abdominal CT** scans within the meta dashboard. 
|
| **Start processsing:**
| Select  *organ-segmentation* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*


.. _workflows_and_extensions radiomics:

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

.. _workflows_and_extensions collect:

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

.. _workflows_and_extensions delete:

Delete images (dcm)
-------------------
| **What's going on?**
| 1) DICOMsare deleted from the PACS.
| 2) Meta data of DICOMs are deleted from the Elasticsearch database.

| **Input data:**
| Filter for DICOMs that you want to remove from the platform. Since in the current verison the files are copied to the local SSD drive, please, do not select too many images at once. 
|
| **Start processsing:**
| Select  *delete-dcm-from-platform* + *BATCH FILE PROCESSING* and click *SEND x RESULTS*

| **Attention**
| In case, you want to resend the images to the server you need to restart the CTP Pod in Kubernetes. In order to this go to Kubernetes, select Namespace "flow", click on "Pods" select the pod named "ctp-..." and then delete the pod by clicking on the trash can on the upper right.

.. _workflows_and_extensions reindex:

Re-index dicoms
---------------
| **What's going on?**
| 1) All meta data saved in Elasticsearch are deleted
| 2) For every DICOM within the PACs the dag extract-metadata is triggered to write the meta data back to Elasticsearch 
 
**Input data:**  
| None
|
| **Start processsing:**
| Trigger the *reindex-pacs* dag manually in Airflow

.. _workflows_and_extensions download:

Download selected files
-----------------------
| **What's going on?**
| 1) DICOMs are zipped and send with a timestamp to the bucket *download* in Minio, where the file can be downloaded

| **Input data:**  
| DICOMs
|
| **Start processsing:**
| Select  *download-selected-files* + *BACTH FILE PROCESSING* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*

.. _workflows_and_extensions extractmetadata:

Extract metadata
-----------------
| **What's going on?**
| 1) Meta data of the DICOM are extracted and written to a JSON file
| 2) The meta data in the JSON file are sent to Elasticsearch

| **Input data:**  
| DICOMs
|
| **Start processsing:**
| Select  *extract-metadata* + *BACTH FILE PROCESSING* or *SINGLE FILE PRCIESSING* and click *SEND x RESULTS*

.. _workflows_and_extensions incomingdcm:

Process incoming dicom
----------------------
| **What's going on?**
| 1) DICOMs sent to the server are saved in the /dcmdata directory and then copied to the local workflow data folder.
| 2) The dag extract-metadata is triggered

| **Input data:**  
| None
|
| **Start processsing:**
| Dag is triggered automatically, once DICOM objects are sent to the server. It should not be triggered manually or with the Kibana dashboard


Extensions
^^^^^^^^^^

.. _workflows_and_extensions code_server:

Code server
-----------
| **What's going on?**
| The code server is used for developing new DAGs and operator for Airflow. It mount the workflows directory of the kaapana

| **Mount point:**  
| <fast_data_dir>/workflows

.. _workflows_and_extensions jupyterlab:

Jupyter lab
-----------
| **What's going on?**
| The Jupyter lab can be used to quickly analyse data that are saved to the object store Minio. We tried to preinstalled most of the common python packages. Please do not use the Jupyter notebook for sophisticated calculations. Here, it is better to write an Airflow DAG

| **Mount point:**  
| <slow_data_dir>/minio

.. _workflows_and_extensions mitk_flow:

MITK Flow
---------
| **What's going on?**
| The MITK Flow is an instance of MITK to watch image data.

| **Mount point:**  
| <slow_data_dir>/minio

.. _workflows_and_extensions tensorboard:

Tensorboard
-----------
| **What's going on?**
| Tensorboard can be launched to analyse generated results during an training, which will come in the future. It also mounts to the Minio directory.

| **Mount point:**  
| <slow_data_dir>/minio



