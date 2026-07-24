.. _hands_on_extension_development_geometric_heads:

============================================================
Hands On Extension Development: Geometric Heads
============================================================

You are a researcher and you are very passionate about spheres. Therefore you are intruiged by the fact that the heads in your CT-scans are **not** perfectly round. And want to therefore "anonymize" the patients in your dataset by replacing their head with perfect round spheres.

To share your passion you also want to make your method broadly available for clinical workers and practicioners.

Because of this you decided to opt for porting your method into kaapana.
The following documents how to develop workflows as extensions in Kaapana, and how to package and distribute them through an OCI repository.
Most of the code is provided, so that you can focus on the main concepts.


What you will build
###################

.. mermaid::

   flowchart LR
      A["Download DICOM"] --> B["DICOM to NRRD"]
      B -- "NRRD" --> C["BodyPartRegression"]
      B -- "NRRD" --> D["Replace the head"]
      C -- "BPR JSON" --> D
      D --> E["NRRD to DICOM"]
      A -- "DICOM Metadata" --> E
      E --> F["Send DICOM"]


While your main goal is to replace a patient's head in a CT scan, this is only one task within the workflow shown above.

Achieving this requires several preprocessing and post-processing steps. Thankfully, Kaapana already provides some of these tasks as reusable processing containers from other workflows.

The complete workflow retrieves the DICOM files from a PACS, converts them to NRRD, runs BodyPartRegression to localize the head, executes your head-replacement method, converts the modified NRRD back to DICOM, and finally sends the modified DICOM files to a PACS.


1. Explore the supplied structure
#################################
The head-replacement workflow we want to create and add to the Kaapana platform, should have the following structure:

.. code-block:: text

   head-replacement-exercise/
   |--- processing-containers/
   |    `--- head-demo-tools/
   |         |--- Dockerfile
   |         |--- processing-container.json
   |         |--- files/demo_tools.py
   |         `--- tasks/replace-head-task.json
   `--- oci/
        |--- extension_manifest.json
        `--- head-replacement/
             |--- workflow_definition.py
             `--- workflow.json

You can find the relevant code under ``data-processing/workflows/head-replacement-exercise``.

Here, we for one have the ``head-demo-tools`` processing-container. It contains the code of our head-replacement method that we want to add in ``files/demo_tools.py``, as well as everyting
needed to run it with Kaapana's Task API. 
The ``oci`` folder contains the workflow definition and the manifest that will be used to package the workflow as an extension.


Lets first focus on the head-replacement method and its processing-container.



2. Your head-replacement method
###############################

The provided ``demo_tools.py`` file contains all the logic of your method. It replaces the head-slices that BodyPartRegression identified in a NRRD volume, with a sphere of roughly the same radius.
It accepts an NRRD CT volume and a BodyPartRegression JSON result as inputs, and produces a modified NRRD volume as output.

.. code-block:: bash
   :caption: Its container command is:

   python3 -u /kaapana/app/demo_tools.py replace-head \
     --input-root /kaapana/app/input-nrrd \
     --bpr-root /kaapana/app/bpr-json \
     --output-root /kaapana/app/output-nrrd

You do not need to modify the algorithm; you only need to package it.


3. Packaging the method as a task
##################################################
In order to run your method in Kaapana, you need to package it as a task and define how it interacts with the other tasks in the workflow.
Most of that logic lives inside the ``processing-container.json`` file.

.. code-block:: text
   :caption: You can find the processing-container.json in:

   data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools/processing-container.json

Define the task template in three parts:

| **Input channels**
Input channels define the path of the input data that the processing-container of your method expects.
Their names must match those of the corresponding output channels, from which the data comes from. In this case, the upstream tasks are the DICOM-to-NRRD conversion and the BodyPartRegression task.
Their mounted paths specify where the container mounts the data internally. You can choose these paths freely.
| Add input channels for:

* The BodyPartRegression result.
* The NRRD produced by the DICOM-to-NRRD conversion task.

You can find the definitions of their output channels
in `data-processing/workflows/registration-workflow/processing-containers/mitk-tools/processing-container.json`
and `data-processing/kaapana-plugin/processing-containers/bodypart-regression-task/processing-container.json`.

| **Output channel**
Similarly, output channels define where the processing-container writes its resulting data.
| Add an output channel to your methods processing container. It will later contain the modified NRRD containing the spherical head.
You can choose both its name and its mounted path freely.


| **Command**
| This defines the command that is executed when the processing-container starts.
| It should invoke your method ``demo_tools.py`` with the arguments required to perform the head
  replacement. Ensure that the script's input and output paths match the
  mounted channel paths.

The starter manifest intentionally contains ``TODO`` values and instructional
comments. Replace the values and remove the comments to produce valid JSON.

.. tabs::

   .. tab:: Exercise

      .. code-block:: json

         {
           "name": "head-demo-tools",
           "description": "Minimal synthetic head replacement for LPS-oriented NRRD volumes.",
           "api_version": 1,
           "templates": [
             {
               // ###########################
               // Exercise: define the replace-head task template.
               //
               // It consumes the channels "nrrd" and "bpr-json",
               // produces "nrrd", and invokes demo_tools.py replace-head.
               // Inspect files/demo_tools.py to find the correct CLI arguments
               // for the command array.
               // ###########################

               "identifier": "replace-head",
               "description": "Orient NRRD to LPS and replace BPR head foreground with a clipped physical sphere.",
               "env": [],
               "inputs": [
                 {
                   "name": "TODO",
                   "mounted_path": "TODO"
                 },
                 {
                   "name": "TODO",
                   "mounted_path": "TODO"
                 }
               ],
               "outputs": [
                 {
                   "name": "TODO",
                   "mounted_path": "TODO"
                 }
               ],
               "command": [
                 "TODO"
               ],

               // ###########################
               // End exercise
               // ###########################

               "resources": {
                 "requests": {
                   "memory": "1Gi"
                 },
                 "limits": {
                   "memory": "6Gi"
                 }
               }
             }
           ]
         }

   .. tab:: Solution

      .. code-block:: json

         {
           "name": "head-demo-tools",
           "description": "Minimal synthetic head replacement for LPS-oriented NRRD volumes.",
           "api_version": 1,
           "templates": [
             {
               "identifier": "replace-head",
               "description": "Orient NRRD to LPS and replace BPR head foreground with a clipped physical sphere.",
               "env": [],
               "inputs": [
                 {
                   "name": "nrrd",
                   "mounted_path": "/kaapana/app/input-nrrd"
                 },
                 {
                   "name": "bpr-json",
                   "mounted_path": "/kaapana/app/bpr-json"
                 }
               ],
               "outputs": [
                 {
                   "name": "nrrd",
                   "mounted_path": "/kaapana/app/output-nrrd"
                 }
               ],
               "command": [
                 "python3",
                 "-u",
                 "/kaapana/app/demo_tools.py",
                 "replace-head",
                 "--input-root",
                 "/kaapana/app/input-nrrd",
                 "--bpr-root",
                 "/kaapana/app/bpr-json",
                 "--output-root",
                 "/kaapana/app/output-nrrd"
               ],
               "resources": {
                 "requests": {
                   "memory": "1Gi"
                 },
                 "limits": {
                   "memory": "6Gi"
                 }
               }
             }
           ]
         }

Validate the completed contract:

.. code-block:: bash

   python3 -m task_api.cli validate \
     data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools/processing-container.json \
     --schema pc

The command must exit without schema errors before you continue.


4. Publishing your task as an Docker image
####################################################

Since each task is run in its own isolated container, the method is packaged as a Docker image:
(We already provided this code for this demo)

.. code-block:: dockerfile

  FROM local-only/base-python-cpu:latest

  LABEL IMAGE="head-demo-tools"
  LABEL VERSION="1.0.0"
  LABEL BUILD_IGNORE="False"

  COPY processing-container.json /
  COPY files/demo_tools.py /kaapana/app/demo_tools.py

  WORKDIR /kaapana/app


.. code-block:: text
   :caption: You can find the Dockerfile here:

   data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools/Dockerfile


When the platform then later wants to run the task, it will pull the image from the registry, do some **magic** and start it as a container. 
We therefore need to make sure that the image is built and pushed to a registry so that the platform can pull it during execution.

Build and push the image to the registry:

.. code-block:: bash

    docker login localhost:5000 --username kaapana --password kaapana

    docker build \
      --tag localhost:5000/head-demo-tools:0.7.0-latest \
      data-processing/workflows/head-replacement-exercise/processing-containers/head-demo-tools

    docker push localhost:5000/head-demo-tools:0.7.0-latest



5. Create the head-replacement workflow
###################################################
Next up we need to create the actual workflow that connects your head-replacement task with the other tasks together as one workflow.

.. mermaid::

   flowchart LR
      A["Download DICOM"] --> B["DICOM to NRRD"]
      B -- "NRRD" --> C["BodyPartRegression"]
      B -- "NRRD" --> D["Replace the head"]
      C -- "BPR JSON" --> D
      D --> E["NRRD to DICOM"]
      A -- "DICOM Metadata" --> E
      E --> F["Send DICOM"]


5.1 Add the head-replacement task
=================================
The workflow is mostly defined in a Python file, where each task is represented by a ``KaapanaTaskOperator``.

.. code-block:: text
   :caption: You can find the workflow_definition.py here:

   data-processing/workflows/head-replacement-exercise/oci/head-replacement/workflow_definition.py

Complete the ``replace_head`` operator. It needs the NRRD from
``convert_to_nrrd`` and the JSON result from ``localize_head``.

.. tabs::

   .. tab:: Exercise

      .. code-block:: python

         # ###########################
         # Exercise: connect head-demo-tools to the workflow.
         #
         # Consume "nrrd" from convert_to_nrrd and "bpr-json"
         # from localize_head. Produce the "nrrd" used by the next task.
         # ###########################

         replace_head = KaapanaTaskOperator(
             task_id="TODO",
             image=f"{DEFAULT_REGISTRY}/TODO:{KAAPANA_BUILD_VERSION}",
             taskTemplate="TODO",
             execution_timeout=timedelta(hours=2),
             iochannel_maps=[
                 IOMapping(
                     upstream_operator=TODO,
                     upstream_output_channel="TODO",
                     input_channel="TODO",
                 ),
                 IOMapping(
                     upstream_operator=TODO,
                     upstream_output_channel="TODO",
                     input_channel="TODO",
                 ),
             ],
         )

         # ###########################
         # End exercise
         # ###########################

   .. tab:: Solution

      .. code-block:: python

         replace_head = KaapanaTaskOperator(
             task_id="replace_head",
             image=f"{DEFAULT_REGISTRY}/head-demo-tools:{KAAPANA_BUILD_VERSION}",
             taskTemplate="replace-head",
             execution_timeout=timedelta(hours=2),
             iochannel_maps=[
                 IOMapping(
                     upstream_operator=convert_to_nrrd,
                     upstream_output_channel="nrrd",
                     input_channel="nrrd",
                 ),
                 IOMapping(
                     upstream_operator=localize_head,
                     upstream_output_channel="bpr-json",
                     input_channel="bpr-json",
                 ),
             ],
         )

The supplied dependency chain schedules this task after localization and before
DICOM conversion tasks:

.. code-block:: python

   (
       download_dataset
       >> convert_to_nrrd
       >> localize_head
       >> replace_head
       >> convert_to_derived_dicom
       >> send_derived_dicoms
   )


6. Build and publish the workflow extension
###########################################

Next up you need to build and publish the workflow extension to an OCI repository.

Build, push, and verify the supplied version:

.. code-block:: bash

   extensionctl build \
     data-processing/workflows/head-replacement-exercise/oci \
     --output data-processing/workflows/head-replacement-exercise/dist

   extensionctl push \
     data-processing/workflows/head-replacement-exercise/dist/head-replacement-extension-v{Resulting Build Version}.tar.gz

   extensionctl list --full

Replace the version with the one resulting from``extensionctl build``.


7. Install and run the extension
################################

#. Open **Extension Manager** in Kaapana.
#. In **Repositories**, add the same OCI registry and repository used with
   ``extensionctl``.
#. In **Catalog**, fetch the repository contents.
#. Install ``head-replacement-extension`` version ``0.2.1`` or the version you
   just published.
#. Open **Workflows V2** and start the new ``head-replacement`` workflow.
#. Wait for all six tasks to succeed.

After the workflow completes, you can inspect the output dataset in the gallery view.
