.. _extensions start:

Extensions
==========

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
| Select  *collect-metadata*  + *BATCH PROCESSING* and click *SEND x RESULTS*


.. _extensions delete:

Delete series from platform (delete-series-from-platform)
---------------------------------------------------------
| **What's going on?**
| 1) DICOMs are deleted from the PACS.
| 2) Meta data of DICOMs are deleted from the Elasticsearch database.

| **Input data:**
| Filter for DICOMs that you want to remove from the platform. Since in the current verison the files are copied to the local SSD drive, please, do not select too many images at once. 
|
| **Start processing:**
| Select  *delete-dcm-from-platform* + *BATCH PROCESSING* and click *SEND x RESULTS*

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
| Select  *download-selected-files* + *BATCH PROCESSING* or *SINGLE FILE PROCESSING* and click *SEND x RESULTS*


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
| Select  *nnunet* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*



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
| Select  *organ-segmentation* + *SINGLE FILE PROCESSING* and click *SEND x RESULTS*


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
| Select  *radiomics* + *BATCH PROCESSING* or *SINGLE FILE PROCESSING* and click *SEND x RESULTS*


Applications
^^^^^^^^^^^^

.. _extensions code_server:

Code server
-----------
| **What's going on?**
| The code server is used for developing new DAGs and operators for Airflow. It mount the workflows directory of the kaapana

| **Mount point:**  
| <fast_data_dir>/workflows

.. _extensions jupyterlab:

Jupyter lab
-----------
| **What's going on?**
| The Jupyter lab can be used to quickly analyse data that are saved to the object store Minio. We tried to preinstall most of the common python packages. Please do not use the Jupyter notebook for sophisticated calculations. Here, it is better to write an Airflow DAG

| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions mitk_flow:

MITK Flow
---------
| **What's going on?**
| The MITK Flow is an instance of MITK to watch image data.

| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions tensorboard:

Tensorboard
-----------
| **What's going on?**
| Tensorboard can be launched to analyse generated results during an training, which will come in the future. It also mounts to the Minio directory.

| **Mount point:**  
| <slow_data_dir>/minio


