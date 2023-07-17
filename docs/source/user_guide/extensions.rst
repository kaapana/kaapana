.. _extensions:

Extensions
##########

Introduction
^^^^^^^^^^^^

.. note::
  This section explains the types of Kaapana extensions and how they work. For descriptions of available workflows and applications, refer to the  :ref:`extensions_workflows` and :ref:`extensions_applications`. 
  To learn how to integrate custom components into the platform as extensions, refer to the :ref:`application_dev_guide` and :ref:`workflow_dev_guide`.


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

The section :ref:`workflow_dev_guide` also explains how to write and add your own extensions.

Uploading Extensions to the Platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Kaapana also provides an experimental upload component for extensions. This allows users to upload both Docker images and the Helm charts to the platform. Currently, this component only accepts two file types: ".tar" for exported images and ".tgz" for Helm charts.

This feature is intended to be used by **developers who have knowledge about configuring Helm charts and Kubernetes resources**. It is strongly recommended to read the following sections before uploading anything to platform: :ref:`helm_charts` and :ref:`how_to_dockerfile`

**Chart Upload:**

* Uploaded chart files are checked for basic safety measures, such as whether they are running any resource under the admin namespace. 
* To create a zipped chart file that can be uploaded to Kaapana, run the following Helm command inside the chart folder:

::

  helm dep up
  helm package .

.. hint::
  
  * If the build step is already completed, all the chart tgz files -and their respective folders- should be available under `kaapana/build/kaapana-admin-chart/kaapana-extension-collection/charts`. The structure should be the same with the DAGs and services already available there.
  * For any Kubernetes resource yaml inside the templates folder (i.e. deployment, job), the image tag should be referenced correctly (`example field that needs to be changed <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/services/hello-world/hello-world-chart/templates/deployment.yaml#L23>`_).



**Image Upload:**

* To save an image as a .tar file, use `docker <https://docs.docker.com/engine/reference/commandline/save/>`_ or `podman <https://docs.podman.io/en/latest/markdown/podman-save.1.html>`_.
* Uploaded images are automatically imported into the microk8s ctr environment (for details see the `images import command here <https://microk8s.io/docs/command-reference#heading--microk8s-ctr>`_) . 
* A useful command to check if the image is imported with the correct tag into the container runtime is :code:`microk8s ctr images ls | grep <image-tag>`

.. hint::
    Since the images uploaded via this component are not already available in a registry, the imagePullPolicy field in the corresponding Kubernetes resource yaml files (`example value to be changed <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/develop/templates_and_examples/examples/services/hello-world/hello-world-chart/templates/deployment.yaml#L24>`_) should be changed to :code:`IfNotPresent`.


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

nnU-Net (nnunet-predict)
-----------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **What's going on?**
| A nnU-Net inference is executed.

| 1) Model is downloaded
| 2) DICOM will be converted to .nrrd files
| 3) Selected task is applied on input image
| 4) .nrrd segmentations will be converted to DICOM Segmentation (DICOM SEG) object.
| 5) DICOM SEGs will be sent to the internal platform PACS

| **Input data:**  
| Depending on the Task see for more information on `Github <https://github.com/MIC-DKFZ/nnUNet>`_

nnU-Net (nnunet-training)
------------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **What's going on?**
| A nnU-Net training is executed.

| 1) Segmentation objects are downloaded
| 2) Referenced DICOM objects are downloaded
| 3) Segmentation objects will be converted to .nifti files
| 4) DICOM will be converted to .nifti files
| 5) The segmentation objects are evaluated for overlapping segmentations and in case of an overlap to a certain threshold, the segmentation object will be removed from the training data. 
| 6) nnU-Net training is planned and training data is preprocessed
| 7) The actual training is executed
| 8) The trained model is zipped
| 9) The zipped model is converted to a DICOM object
| 10) The DICOM object is sent to the internal platform PACS
| 11) A training report is generated
| 12) The model and training logs are uploaded to Minio
| 13) The training report is uploaded to a location, where it can be rendered by a static website
| 14) The training report is converted to a DICOM object 
| 15) The DICOM object is sent to the internal platform PACS

| **Input data:**  
| Segmentation objects. Please avoid overlapping segmentations and specify the segmentation labels that you want to use for the training in the *SEG* field.

nnU-Net (nnunet-ensemble)
------------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **What's going on?**
| The workflow allows to evaluate the performance of multiple trained nnU-Net models on a given dataset. It could also be used to only evaluate one model. The *seg-check-ensemble* operator will throw an error but the execution is still successful!

| 1) Segmentation objects used as reference segmentations are downloaded
| 2) Sorting of segmentation objects
| 2) Referenced DICOM objects are downloaded
| 3) Segmentation objects will be converted to .nifti files
| 4) DICOM will be converted to .nifti files
| 5) The reference segmentation objects are evaluated for overlapping segmentations and in case of an overlap to a certain threshold, the segmentation object will be removed for the evaluation. 
| 6) Models to be evaluated are downloaded
| 7) Models are extracted from DIOCM objects
| 8) Models are unzipped
| 9) Models are applied to the input DICOM data
| 10) Model predictions are ensembled
| 11) The predicted segmentations are restructured
| 12) The ensembled segmentations are restructured
| 13) The predicted segmentation objects are evaluated for overlapping segmentations and in case of an overlap to a certain threshold, the segmentation object will be removed for the evaluation.
| 14) The ensembled segmentation objects are evaluated for overlapping segmentations and in case of an overlap to a certain threshold, the segmentation object will be removed for the evaluation.
| 15) DICE scores between the reference and predicted (ensembled) segmentations are calculated
| 16) A report containing the DICE Scores is created
| 17) The results of the evaluation are uploaded to Minio
| 18) A report is uploaded to a location, where it can be rendered by a static website

| **Input data:**  
| Segmentation objects. Please avoid overlapping segmentations. In addition, models to be used for the evaluation are expected. Make sure that the models actually predict the labels from the inputted segmentation objects.


nnU-Net (nnunet-model-management)
--------------------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **What's going on?**
| Models that are stored as DICOM files in the internal PACS can be extracted into the *models* directory of Kaapana to be used by the nnunet-predict workflow. The workflow also allows to remove installed tasks.

| 1) Models are downloaded
| 2) Models are extracted from DIOCM objects
| 3) Models are moved to the *models* directory of Kaapana

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

.. _extensions_mitk_flow:

MITK Flow
---------
| **What's going on?**
| 1) A MITK instance is launched within a noVNC application.
| 2) Access the noVNC application with MITK running through the Pending applications page.
| 3) In MITK, load the first task from the Kaapana Task List **Load task 1/x**.
| 4) Modify or create segmentations.
| 5) Accept the segmentations by clicking **Accept segmentation**. Only accepted segmentations will be stored.
| 6) Load the next task.
| 7) After completing manual interactions, click **Finish Manual Interaction** on the Pending applications page. Newly created segmentations will be uploaded to the PACS.

| **Notes:**
| The *mitk-flow* workflow aims to generate segmentations using MITK tools.
| Inside the initialized MITK application, a task list is created, containing all series selected in the workflow. Depending on the input data, there are two possibilities to create new segmentations:

| 1) If the input data is an image series, a new segmentation can be directly created.
| 2) If a segmentation is selected as input data, the corresponding image and segmentation are preloaded. The modified segmentation is then stored as a new segmentation in the PACS.

| Once you have completed your work with all series (all tasks are done), all accepted segmentations will be sent to the PACS upon finishing the manual interaction.
| In the datasets view, the segmentations are tagged as "MITK-flow".
| If no segmentations were created or no project was saved, the **workflow will fail** because the :code:`DcmSendOperator` fails when no data is sent.


| **Input data:**  
| DICOMs

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
| The MITK Workbench is an instance of `MITK <https://www.mitk.org>`__ running in a pod.


| **Mount point:**  
| <slow_data_dir>/minio

.. _extensions_tensorboard:

Tensorboard
-----------
| **What's going on?**
| Tensorboard can be launched to analyse generated results during a training, which will come in the future. It also mounts to the Minio directory.

| **Mount point:**  
| <slow_data_dir>/minio


