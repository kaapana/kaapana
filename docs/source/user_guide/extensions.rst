.. _extensions:

Extensions
##########

Introduction
^^^^^^^^^^^^

.. note::
  This section explains the types of Kaapana extensions and how they work. For descriptions of available workflow and application extensions, refer to the  :ref:`extensions_workflows` and :ref:`extensions_applications`. 
  To learn how to integrate custom components into the platform as extensions, refer to the :ref:`application_dev_guide` and :ref:`workflow_dev_guide`.


The *Extension* functional unit in Kaapana serves as an app store. It allows users to install/uninstall applications, workflows, and even platforms (experimental feature). Technically, an extension is a `Helm chart <https://helm.sh/docs/topics/charts/>`_. 

Each extension in the Kaapana repository consists of two folders: :code:`docker` and :code:`<extension-name>-chart`. For more information about the file structure, refer to the Helm Charts section :ref:`helm_charts`.

There are two types of extensions:

1. **Workflow Extensions**: Consist of single or multiple executable DAGs in `Apache Airflow <https://airflow.apache.org/>`_. After installing a workflow extension, you can see the DAGs available under Workflow Execution menu.
2. **Applications**: These provide additional functionalities such as opening a VS Code server, a JupyterLab notebook, or an MITK Workbench instance.

In addition to the distinction in kinds, there is also an distinction in versions, namely *stable* or *experimental*. Stable extensions **have been tested and maintained**, while experimental extensions are not. The filters on the Extensions page allow users to filter extensions based on the version. The extension list is updated in real time based on the selected filters. The Extensions page also displays the current Helm and Kubernetes status of each extension, such as :code:`Running`, :code:`Completed`, :code:`Failed`, or :code:`Error`.

.. note::

  Kaapana supports multi-installable extensions, which will have a "Launch" button instead of "Install". Each time a multi-installable extension is launched, it is deployed as a separate Helm release.

.. hint::

  To install a specific version of an extension, use the dropdown in the version column.

The section :ref:`workflow_dev_guide` also explains how to write and add your own extensions.

Uploading Extensions to the Platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Kaapana also provides an experimental upload component for extensions. This allows users to upload both Docker images and Helm charts to the platform. Currently, this component only accepts two file types: ".tar" for exported images and ".tgz" for Helm charts.

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


If you have any issues regarding the upload mechanism, check :ref:`extension_container_upload_fail`.

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

nnunet-predict
--------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **Workflow Overview**
| A nnU-Net inference is executed.

| 1) Model is downloaded
| 2) DICOM is converted to .nifti files
| 3) The model runs inference on the input data
| 4) Segmentations are converted to DICOM Segmentation (DICOM SEG) objects
| 5) DICOM SEG objects are sent to the internal platform PACS

| **Input data:**  
| A trained nnU-Net model that is already installed via *nnunet-install-model* workflow.

nnunet-training
---------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **Workflow Overview**
| A nnU-Net training is executed.

| 1) Segmentation objects are downloaded
| 2) Referenced DICOM images are downloaded
| 3) DICOM images are converted to .nifti files
| 4) Segmentation masks are converted to .nifti files
| 5) If specified in input form, segmentation masks are filtered based on keywords "Keep: <label>" and "Ignore: <label>"
| 6) If specified in input form, multiple labels are fused into a new label
| 7) If specified in input form, label are renamed
| 8) The segmentation masks are evaluated for overlapping segmentations and if the overlap is above a certain threshold, the segmentation object is removed from training data
| 9) nnU-Net training is planned and training data is preprocessed
| 10) The actual training is executed
| 11) The trained model is zipped
| 12) The zipped model is converted to a DICOM object
| 13) The DICOM object is sent to the internal platform PACS
| 14) A training report is generated
| 15) The model and training logs are uploaded to Minio
| 16) The training report is uploaded to a location, where it can be rendered by a static website
| 17) The training report is converted to a DICOM object 
| 18) The DICOM object is sent to the internal platform PACS

| **Input data:**  
| Segmentation objects. Please avoid overlapping segmentations and specify the segmentation labels that you want to use for the training in the *SEG* field.

nnunet-ensemble
-------------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **Workflow Overview**
| Evaluates the performance of multiple trained nnU-Net models on a given dataset. This workflow can also be used to evaluate only one model, where the *seg-check-ensemble* operator throws an error, but the execution is still successful.

| 1) Segmentation objects used as reference segmentations are downloaded
| 2) Segmentation objects are sorted
| 3) Referenced DICOM images are downloaded
| 4) DICOM images are converted to .nifti files
| 5) Models to be evaluated are downloaded
| 6) Models are extracted from DIOCM objects and unzipped
| 7) Models are applied to the DICOM images
| 8) The predicted segmentations are restructured
| 9) The predicted segmentations are evaluated for overlapping segmentations and if the overlap is above a certain threshold, they removed from the evaluation
| 10) Model predictions are ensembled
| 11) The ensembled segmentations are restructured
| 12) The ensembled segmentations are evaluated for overlapping segmentations and if the overlap is above a certain threshold, they removed from the evaluation
| 13) The reference segmentations are converted to .nifti files
| 14) If specified in input form, segmentation masks are filtered based on keywords "Keep: <label>" and "Ignore: <label>"
| 15) If specified in input form, multiple labels are fused into a new label
| 16) If specified in input form, labels are renamed
| 17) The reference segmentations are evaluated for overlapping segmentations and and if the overlap is above a certain threshold, they removed from the evaluation
| 18) DICE scores between the reference and predicted (ensembled) segmentations are calculated
| 19) A report containing the DICE scores is created
| 20) The evaluation results are uploaded to Minio
| 21) A report is uploaded to a location, where it can be rendered by a static website

| **Input data:**  
| Segmentation objects and models for evaluation. Please avoid overlapping segmentations, and make sure that the models predict the labels from the input (reference) segmentations.


nnunet-install-model
--------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **Workflow Overview**
| Models that are stored as DICOM files the internal PACS are installed into the *models* directory of Kaapana. Installed models can be used in nnunet-predict and ensemble workflows.

| **Input data:**
| Dataset that stores nnunet models as DICOM files. If the dataset contains any modality other than **OT**, the workflow will fail. Use the Datasets view to filter for the right model.

nnunet-uninstall-models
-----------------------
| **Method:** "Automated Design of Deep Learning Methods for Biomedical Image Segmentation"
| **Authors:**  Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein
| **Cite as:** `arXiv:1904.08128 [cs.CV] <https://arxiv.org/abs/1904.08128>`_

| **Workflow Overview**
| Installed models inside the *models* directory of Kaapana are uninstalled. Models still persist in the internal PACS as DICOM files.

| **Input data:**
| Installed model name.

TotalSegmentator
----------------
| **Method:** "TotalSegmentator: robust segmentation of 104 anatomical structures in CT images"
| **Authors:**  Wasserthal J., Meyer M., Breit H., Cyriac J., Yang S., Segeroth M.
| **DOI:** `10.48550/arXiv.2208.05868 <https://arxiv.org/abs/2208.05868>`_
| **Code:** `https://github.com/wasserth/TotalSegmentator <https://github.com/wasserth/TotalSegmentator>`_

| **Workflow Overview**
| 1) Model is downloaded
| 2) DICOM is converted to .nrrd files
| 3) TotalSegmentator with all its subtasks is applied to the input data
| 4) .nrrd segmentations will be converted to DICOM Segmentation (DICOM SEG) object
| 5) DICOM SEGs will be sent to the internal platform PACS

| **Input data:**  
| Any **CT** scans.


.. _extensions_organseg:

Automatic organ segmentation (shapemodel-organ-seg)
---------------------------------------------------
| **Method:** "3D Statistical Shape Models Incorporating Landmark-Wise Random Regression Forests for Omni-Directional Landmark Detection"
| **Authors:**  Tobias Norajitra and Klaus H. Maier-Hein
| **DOI:** `10.1109/TMI.2016.2600502 <https://ieeexplore.ieee.org/document/7544533>`_

| **Workflow Overview**
| 1) DICOMs are converted to .nrrd files
| 2) Input images are normalized
| 3) Parallel segmentation of liver,spleen and kidneys (left and right)
| 4) .nrrd segmentations will be converted to DICOM Segmentation (DICOM SEG) object
| 5) DICOM SEGs are sent to the internal platform PACS

| **Input data:**  
| Filter for **abdominal CT** scans using the **Datasets** view. 


.. _extensions_radiomics:

Radiomics (radiomics-dcmseg)
----------------------------

| **Workflow Overview**
| 1) Selected DICOM SEGs are converted to .nrrd files
| 2) Corresponding CT file is downloaded form the PACS
| 3) Downloaded CT files are converted to \*.nrrd
| 4) Radiomics is applied on selected DICOMs
| 5) Extracted radiomics data are pushed to the bucket *radiomics* in Minio and can be downloaded there

| **Input data:**  
| DICOM Segmentations 

.. _extensions_mitk_flow:

MITK Flow
---------
| **Workflow Overview**
| 1) A MITK instance is launched within a noVNC application
| 2) Access the noVNC application with MITK running through the Pending applications page
| 3) In MITK, load the first task from the Kaapana Task List **Load task 1/x**
| 4) Modify or create segmentations
| 5) Accept the segmentations by clicking **Accept segmentation**. Only accepted segmentations are stored
| 6) Load the next task
| 7) After completing manual interactions, click **Finish Manual Interaction** on the Pending applications page. Newly created segmentations are uploaded to the PACS

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

.. _extensions_classification:


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

.. _extensions_collabora:

Collabora
---------

.. _extensions_edk:

Extension Development Kit (EDK)
-------------------------------

Starting from v0.4.0, Kaapana provides an extension development environment where users can build extensions directly inside the platform.
EDK deploys a VS Code server environment for the development of container images and Helm charts, and a local registry where the built container images can be pushed to or pulled from.
Note that currently, EDK only includes ease-of-use scripts for workflow extensions, not for application extensions.
Once you install EDK, proceed to the VS Code server by using the first link next to the application name. There are a couple of scripts for building images, charts, or directly an entire extension. Please refer to the :code:`README.md` inside for more details.
To initialize the development environment, navigate to :code:`cd /kaapana/app` and run :code:`./init.sh` inside the terminal. This script builds all the Kaapana base images and pushes them to the local registry. Once it completes, you can check the images in the local registry by following the second link.
For convenience, the init script copies an example pyradiomics extractor DAG under the :code:`dag` folder. You can build this extension directly by running :code:`./build_extension.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor`. After this command is successfully executed, the extension should be available on the Extensions page (make sure that you change the Version filter to "All" on the Extensions page).
This example DAG can be used as a template for building your own extensions. The easiest way to start modifying it is to change the script `processing-containers/pyradiomics-feature-extractor/files/extract_features.py` and rebuild it. This only changes the container that the operator :code:`PyradiomicsExtractorOperator` pulls, and the rest of the DAG stays the same.
Once you have a better understanding of this DAG, you can start adapting the DAG definition file or even add more operators and containers that they pull. In the end, you should be able to write and deploy your own custom workflow extensions directly inside EDK and test them easily on your platform.

.. _extensions_jupyterlab:

JupyterLab
-----------
The `JupyterLab <https://jupyter.org/>`__ is an excellent tool to swiftly analyse data stored to the MinIO object store.
It comes preinstalled with a wide array of commonly used Python packages for data analysis.
You can deploy multiple instances of JupyterLab simultaneously, each with its dedicated MinIO bucket named after the respective JupyterLab instance.
Data stored within this bucket is available to the JupyterLab application through the `/minio/input` directory.
You can save your analysis-scripts or results to the directory `/minio/output`.
Files in this directory will be automatically transfered to and persisted in the MinIO bucket named `output` and are available to the `JupyterlabReportingOperator`.
While JupyterLab is great for exploratory data analysis, for more complex calculations, consider developing a dedicated Airflow DAG.

| **Mount point:**  
| <slow_data_dir>/applications/jupyterlab/<jupyterlab-instance-name>/input
| <slow_data_dir>/applications/jupyterlab/<jupyterlab-instance-name>/output


.. _extensions_minio_sync:

MinIO Sync
----------

.. _extensions_mitk_workbench:

MITK Workbench
--------------
The MITK Workbench is an instance of `MITK <https://www.mitk.org>`__ running in a container and available to users via Virtual Network Computing (VNC).
Multiple instances of MITK can be deployed simultaneously.
For each deployment a dedicated MinIO bucket is created, named after the respective MITK instance.
To import data into the running MITK container, upload your data to the `/input` directory within this MinIO bucket.
All data stored at this path of the MinIO bucket will be transferred to the `/input` directory of the MITK container.
If you wish to retrieve your results from the MITK application, ensure to save them to the `/output` directory within the MITK container.
Any data placed in this directory will be automatically transferred to the `/output` directory within the dedicated MinIO bucket.

| **Mount point:**  
| <slow_data_dir>/applications/mitk/<mitk-instance-name>/input
| <slow_data_dir>/applications/mitk/<mitk-instance-name>/output

.. _extensions_slicer_workbench:

Slicer Workbench
----------------
The Slicer workbench is an instance of `3D Slicer <https://slicer.org/>`__ running in a container and available to users via Virtual Network Computing (VNC).
Multiple instances of Slicer can be deployed simultaneously.
For each deployment a dedicated MinIO bucket is created, named after the respective Slicer instance.
To import data into the running Slicer container, upload your data to the `/input` directory within this MinIO bucket.
All data stored at this path of the MinIO bucket will be transferred to the `/input` directory of the Slicer container.
If you wish to retrieve your results from the Slicer application, ensure to save them to the `/output` directory within the Slicer container.
Any data placed in this directory will be automatically transferred to the `/output` directory within the dedicated MinIO bucket.

| **Mount point:**  
| <slow_data_dir>/applications/slicer/<slicer-instance-name>/input
| <slow_data_dir>/applications/slicer/<slicer-instance-name>/output

.. _extensions_tensorboard:

Tensorboard
-----------
`Tensorboard <https://www.tensorflow.org/tensorboard>`__ can be launched to analyse results generated during a training.
Multiple instances of Tensorboard can be deployed simultaneously.
For each deployment a dedicated MinIO bucket is created, named after the respective Tensorboard instance.
Data stored within this bucket are available to the Tensorboard application.

| **Mount point:**  
| <slow_data_dir>/applications/tensorboard/<tensorboard-instance-name>


