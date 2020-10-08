.. _start_a_workflow_doc:

Trigger a workflow
==================

As the platforms main purpose is to apply processing pipelines to images a short guide of how a typical workflow would look like

- Send images that you would like to process to the server. (cf. :ref:`send_images_to_the_platform_doc`)
- Once the DICOMs are on the platform you can exmamine its meta data on the Kibana dashboard. With this dashboard you can also filter the data
  on that you would like to apply processing pipeline. Filtering in Kibana works by clicking on the plus signs or the lines/bars in the graphics or by
  designing a custom filter at the top left
- After defining a cohort you can select a workflow that you want to trigger. You have the possibilty to choose between Batch and Single
  file processing. This means, if for every selected object a seperate pipeline should be started or if only one pipeline for all objects is started. Most
  of the time batch processing is the right choice
- Click on *SEND x RESULTS* to start the workflow
- Now you can move to Airflow in order to see and debug how your workflow is going. By clicking on the dag you get an overview of the different processing 
  steps (operators) that are performed during the pipeline. By clicking on an operator and then on logs, you can see what the opertor outputs during its computation
- Workflows output for example DICOM Segmentations or json/csv files. On the OHIF viewer you can look at possible generated DICOMs and on Minio you 
  find normally in the bucket named like the dag the output that was performed during the workflow
