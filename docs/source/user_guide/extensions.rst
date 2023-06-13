.. _extensions:

Extensions
##########

Introduction
^^^^^^^^^^^^

.. note::
  This section explains the types of Kaapana extensions and how they work. For descriptions of available workflows and applications, refer to the  :ref:`extensions_workflows` and :ref:`extensions_applications`. 
  To learn how to integrate custom components into the platform as extensions, refer to the :ref:`service_dev_guide` and :ref:`processing_dev_guide`.


The *Extension* functional unit in Kaapana serves as an app store. It allows users to install/uninstall applications, workflows, and even platforms (experimental feature). Technically, an extension is a `Helm chart <https://helm.sh/docs/topics/charts/>`_. 

Each extension in the Kaapana repository consists of two folders: :code:`docker` and :code:`<extension-name>-chart`. For more information about the file structure, refer to the Helm Charts section :ref:`helm_charts`.

There are two types of extensions (excluding the experimental "platforms"):

1. Workflows: These are algorithms executed via `Apache Airflow <https://airflow.apache.org/>`_.
2. Applications: These provide additional functionalities such as opening a VS Code server, a JupyterLab notebook, or an MITK Workbench instance.

In addition to the distinction in kinds, there is also an distinction in versions, namely *stable* or *experimental*. Stable extensions **have been tested and maintained**, while experimental extensions are not. The filters on the Extensions page allow users to filter extensions based on the version. The extension list is updated in real time based on the selected filters. The Extensions page also displays the current Helm and Kubernetes status of each extension, such as :code:`Running`, :code:`Completed`, :code:`Failed`, or :code:`Error`.

.. note::

  Kaapana supports multi-installable extensions, which will have a "Launch" button instead of "Install". Each time a multi-installable extension is launched, it is deployed as a separate Helm release.

.. hint::

  To install a specific version of an extension, use the dropdown in the version column.

The section :ref:`processing_dev_guide` also explains how to write and add your own extensions.

Uploading Extensions to the Platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Kaapana also provides an upload component for extensions. This allows users to upload both Docker containers and the Helm charts to the platform. Currently, this component only accepts two file types: ".tar" for exported containers and ".tgz" for Helm charts.

**Chart Upload:**

* Uploaded chart files are checked for basic safety measures, such as whether they are running any resource under the admin namespace. 
* To create a zipped chart file that can be uploaded to Kaapana, run the following Helm command inside the chart folder:

::

  helm dep up
  helm package .

**Container Upload:**

* Uploaded containers are automatically imported into the microk8s ctr environment (for details see the `images import command here <https://microk8s.io/docs/command-reference#heading--microk8s-ctr>`_) . 
* To save an image as a .tar file, use `docker <https://docs.docker.com/engine/reference/commandline/save/>`_ or `podman <https://docs.podman.io/en/latest/markdown/podman-save.1.html>`_.


Extension Parameters
^^^^^^^^^^^^^^^^^^^^

Introduced in version 0.2.0, Extensions support specifying parameters as environment variables. This functionality can be customized according to the requirements of the extension. Some examples of available parameters are :code:`task_ID`s for **nnUNet** and the :code:`service_type`` field for **MITK Workbench**. Parameters can be of type :code:`string`, :code:`boolean`, :code:`single_selectable`, or :code:`multi_selectable`. Parameters should be defined in the values.yaml file of the chart. Each of them should follow this structure:

.. code-block::

  extension_params:
    <parameter_name>:
      default: <default_value>
      definition: "definition of the parameter"
      type: oneof (string, bool, list_single, list_multi)
      value: <value_entered_by_the_user>


.. _extensions_workflows:

Workflows
^^^^^^^^^

.. _extensions_nnunet:

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



.. _extensions_organseg:

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


.. _extensions_radiomics:

Radiomics (radiomics-dcmseg)
----------------------------

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

.. _extensions_mitk_flow:

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

.. _extensions_applications:

Applications
^^^^^^^^^^^^

.. _extensions_code_server:

Code server
-----------
| **What's going on?**
| The code server is used for developing new DAGs and operators for Airflow. It mounts the workflows directory of kaapana

| **Mount point:**  
| <fast_data_dir>/workflows

| **VSCode settings:**
| If you want to use your costum VSCode settings inside the code-server you can save them under :code:`/kaapana/app/.vscode/settings.json`.


.. _extensions_jupyterlab:

Jupyter lab
-----------
| **What's going on?**
| The Jupyter lab can be used to quickly analyse data that are saved to the object store Minio. We tried to preinstall most of the common python packages. Please do not use the Jupyter notebook for sophisticated calculations. Here, it is better to write an Airflow DAG

| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions_mitk_workbench:

MITK Workbench
--------------
| **What's going on?**
| The MITK Workbench is an instance of MITK to watch image data.

| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions_tensorboard:

Tensorboard
-----------
| **What's going on?**
| Tensorboard can be launched to analyse generated results during a training, which will come in the future. It also mounts to the Minio directory.

| **Mount point:**  
| <slow_data_dir>/minio


