.. _extensions start:

Kaapana Extensions
##################

Introduction
^^^^^^^^^^^^
The *Extension* functional unit can be considered as an app store.
It allows (un-)installing components, which can either be workflows or applications.
Workflows are algorithms which are executed via `Apache Airflow <https://airflow.apache.org/>`_.
In addition to the distinction in kinds, there is also an distinction in version, either *stable* or *experimental*.
*Experimental* extensions are not properly tested yet, while *stable* extensions are. There are filters on top of the extension functional unit page, which allow to filter by those criteria.
The filters are automatically applied and will update the extension list below.
For each extension in the list, there is a button for installing or uninstalling, depending on the current status.
When clicking the *install* button, the extension will be downloaded and installed. The current helm and kubernetes status of the freshly installed extension can be seen in the respective columns.
For installing a specific version of an extension, the dropdown in the *version* column can be used.
Uninstalling an extension is as easy as installing one by clicking on *uninstall* for the respective extension in the extension list.

A detailed description of available workflows and applications can be found in :ref:`extensions workflows` and :ref:`extensions applications`.
Information about how to integrate custom components into the platform via the *Extension* functional unit can be found at :ref:`service_dev_guide` and :ref:`processing_dev_guide`.

.. _extensions workflows:

Workflows
^^^^^^^^^

.. _extensions collect:

Collect metadata (collect-metadata)
-----------------------------------
| **What's going on?**
| 1) DICOMs are anonymized by removing a list of personal tags
| 2) Meta data of the DICOMs are extracted and written to JSON files
| 3) JSON files are concatenated to one JSON file.
| 4) JSON file is zipped and send with a timestamp to the bucket *download* in Minio, where the file can be downloaded

| **Input data:**
| DICOMs
|
| **Start processing:**
| Select  *collect-metadata* + *START*, make sure *single execution* on the configuration popup is set to False and then click *START* again.


.. _extensions delete:

Delete series from platform (delete-series-from-platform)
---------------------------------------------------------
| **What's going on?**
| 1) DICOMs are deleted from the PACS.
| 2) Meta data of DICOMs are deleted from the OpenSearch database.

| **Input data:**
| Filter for DICOMs that you want to remove from the platform. Since in the current verison the files are copied to the local SSD drive, please, do not select too many images at once. 
|
| **Start processing:**
| Select  *delete-dcm-from-platform* + *START*, make sure *single execution* on the configuration popup is set to False and then click *START* again.

.. hint::

  | DCM4CHEE needs some time (maybe around 10-15 min) to fully delete the images.

.. _extensions download:

Download series from platform (download-selected-files)
-------------------------------------------------------
| **What's going on?**
| 1) DICOMs are send to the bucket *download* in Minio. If the option zipped is used, they are saved with a timestamp in the *download* bucket.

| **Input data:**  
| DICOMs
|
| **Start processing:**
| Select  *download-selected-files* + *START*, *single execution* on the configuration popup can be set to True or False and then click *START* again.


.. _extensions nnunet:

nnUNet (nnunet-predict)
-----------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **What's going on?**
| 1) Model is downloaded
| 2) DICOM will be converted to .nrrd files
| 3) Selected task is applied on input image
| 4) .nrrd segmentations will be converted to DICOM Segmentation (DICOM SEG) object.
| 5) DICOM SEGs will be sent to the internal platform PACS

| **Input data:**  
| Depending on the Task see for more information on `Github <https://github.com/MIC-DKFZ/nnUNet>`_
|
| **Start processing:**
| Select  *nnunet* + *START*, make sure *single execution* on the configuration popup is set to True and then click *START* again.



.. _extensions organseg:

Automatic organ segmentation (shapemodel-organ-seg)
---------------------------------------------------
| **Method:** "3D Statistical Shape Models Incorporating Landmark-Wise Random Regression Forests for Omni-Directional Landmark Detection"
| **Authors:**  Tobias Norajitra and Klaus H. Maier-Hein
| **DOI:** `10.1109/TMI.2016.2600502 <https://ieeexplore.ieee.org/document/7544533>`_

| **What's going on?**
| 1) DICOM will be converted to .nrrd files
| 2) Normalization of input images
| 3) Parallel segmentation of liver,spleen and kidneys (left and right)
| 4) .nrrd segmentations will be converted to DICOM Segmentation (DICOM SEG) object.
| 5) DICOM SEGs will be sent to the internal platform PACS

| **Input data:**  
| Filter for **abdominal CT** scans within the meta dashboard. 
|
| **Start processing:**
| Select  *organ-segmentation* + *START*, make sure *single execution* on the configuration popup is set to True and then click *START* again.


.. _extensions radiomics:

Radiomics (radiomics-dcmseg)
----------------------------
**TBA**

| **What's going on?**
| 1) Selected DICOM SEGs are converted not .nrrd files
| 2) Corresponding CT file is downloaded form the PACS
| 3) Downloaded CT files are converted to \*.nrrd
| 4) Radiomics is applied on selected DICOMs
| 5) Extracted radiomics data are pushed to the bucket *radiomics* in Minio and can be downloaded there

| **Input data:**  
| DICOM Segmentations 
|
| **Start processing:**
| Select  *radiomics* + *START*, *single execution* on the configuration popup can be set to True or False and then click *START* again.

.. _extensions mitk_flow:

MITK Flow
---------
| **What's going on?**
| 1) A MITK instance is started in a noVNC application.
| 2) The noVNC application with MITK running can be accessed via the *Pending applications* page.
| 3) After finishing manual interaction newly created segmentations are uploaed to the PACS.

| **Notes:**
| The *mitk-flow* workflow is intended to generate segmentations with MITK tools.
  Inside the initialized MITK application only a single series is available.
  If your work with this series is finished, save the project and exit the MITK application.
  Within noVNC MITK will automatically be restarted with the next series available.
  After finishing the manual interaction all created segmentations will be send to the PACS.
  In the Kibana-Dashboard the segmentations are tagged as "MITK-flow".
  If no segmentations were created or no project was saved, 
  **the workflow will fail** because the :code:`DcmSendOperator` fails when no data was send.

| **Input data:**  
| DICOMs

| **Start processing:**
| Select *mitk-flow* + *START*, make sure *single execution* on the configuration popup is set to False and then click *START* again.

.. _extensions applications:

Applications
^^^^^^^^^^^^

.. _extensions code_server:

Code server
-----------
| **What's going on?**
| The code server is used for developing new DAGs and operators for Airflow. It mounts the workflows directory of kaapana

| **Mount point:**  
| <fast_data_dir>/workflows

| **VSCode settings:**
| If you want to use your costum VSCode settings inside the code-server you can save them under :code:`/kaapana/app/.vscode/settings.json`.


.. _extensions jupyterlab:

Jupyter lab
-----------
| **What's going on?**
| The Jupyter lab can be used to quickly analyse data that are saved to the object store Minio. We tried to preinstall most of the common python packages. Please do not use the Jupyter notebook for sophisticated calculations. Here, it is better to write an Airflow DAG

| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions mitk_workbench:

MITK Workbench
--------------
| **What's going on?**
| The MITK Workbench is an instance of MITK to watch image data.

| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions tensorboard:

Tensorboard
-----------
| **What's going on?**
| Tensorboard can be launched to analyse generated results during a training, which will come in the future. It also mounts to the Minio directory.

| **Mount point:**  
| <slow_data_dir>/minio


