.. _extensions start:

Kaapana Extensions
##################

Introduction
^^^^^^^^^^^^
The *Extension* functional unit can be considered as an app store of Kaapana.
It allows installing/uninstalling applications, workflows and even platforms(experimental).
In a more technical sense, an extension is essentially a `Helm chart <https://helm.sh/docs/topics/charts/>`. A Helm chart is a structured way of deploying different Kubernetes resources, which consist of containers. That is why in the Kaapana repository, each extension always has two folders named `docker` and `<extension-name>-chart`.
More info about the file structure can be found in :ref:`helm_charts`

There are two types of extensions (excluding the experimental "platforms"):
1. Workflows are algorithms which are executed via `Apache Airflow <https://airflow.apache.org/>`_.
2. Applications allow supporting additional functionalities such as opening a VS code server, a jupyterlab notebook or an mitk workbench instance.

In addition to the distinction in kinds, there is also an distinction in versions, namely *stable* or *experimental*.
*Experimental* extensions are not properly tested yet, while *stable* extensions are. The filters on top of the Extensions page allow filtering with respect to this versioning.
These filters will update the extension list below in real time.
Also for each extension in the list, it is possible to see the current helm and kubernetes status in the respective columns as Runnning, Completed, Failed, Error etc.
For installing a specific version of an extension, the dropdown in the version column can be used. It is also possible to force uninstall an extension if it is in a Pending state.

A detailed description of available workflows and applications can be found in :ref:`extensions workflows` and :ref:`extensions applications`.
Information about how to integrate custom components into the platform via the *Extension* functional unit can be found at :ref:`service_dev_guide` and :ref:`processing_dev_guide`.


Extension Parameters
^^^^^^^^^^^^^^^^^^^^
One of the new features introduced in 0.2.0 for Extensions is that it is possible to specify parameters that are passed to extensions as environment variables. 
This is a general purpose functionality and can be tailored with respect to the requirements of the extension. 
Some of the examples that are already available are the task IDs for nnunet, which is a multi selectable list of models that will be downloaded during the installation of the extension, and the service type field for mitk-workbench, which specifies the service type as either NodePort or ClusterIP.
A parameter can either be a string, a boolean, a single selectable or a multi selectable list. They should be defined in values.yaml file for the chart and each parameter should have the following structure:

.. code-block::

extension_params:
  <parameter_name>:
    default: <default_value>
    definition: "definition of the parameter"
    type: oneof (string, bool, list_single, list_multi)
    value: <value_entered_by_the_user>

Uploading Extensions to the Platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Version 0.2.0 also introduces the upload component for extensions. This is a useful way of uploading both the docker container and the Helm chart to the platform.
Currently, this component only accepts two file types: ".tar" for exported docker containers and ".tgz" for Helm charts. 

Chart upload 

* Uploaded chart files will be checked for basic safety measures, such as whether or not it is running any resource under the admin namespace.
* In order to create a zipped chart file that can be uploaded to Kaapana, users should run the following helm command inside of the chart folder

::

  helm dep up
  helm package .


Container Upload:

* Uploaded containers will be automatically imported into the microk8s ctr environment (for details see the `images import command here <https://microk8s.io/docs/command-reference#heading--microk8s-ctr>`) 
* For container upload, it is possible to save an image as a .tar file using `docker <https://docs.docker.com/engine/reference/commandline/save/>` or `podman <https://docs.podman.io/en/latest/markdown/podman-save.1.html>`.


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


