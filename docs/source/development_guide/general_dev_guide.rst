.. _general_dev_guide:

=======
General
=======

Introduction
------------

This guide is intended to provide a quick and easy way to get started with developments on the platform.
 
The guide currently consists of three parts. This part gives a brief overview over the technologies and needed preparations for the rest of the guide.
The part :ref:`processing_dev_guide` does focus on the implementation of pipelines for Airflow in order to apply processing steps to images. 
It explains how to implement an Airflow-DAG and integrate it as an extension into the Kaapana technology stack.
The last section :ref:`service_dev_guide` gives step by step instructions for how to deploy a general--purpose web application within Kaapana as an example how arbitrary new components can be added to the platform.


Getting started
---------------

List of the technologies used within this guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These tutorials/technologies are good references, when starting with the Kaapana deployment:

* `Docker <https://docs.docker.com/get-docker/>`_: Necessary when you want to build container on your local machine
* `Airflow <https://airflow.apache.org/docs/stable/>`_: Our pipeline tool for processing algorithms
* `Kubernetes <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`_: (Advanced) On your local machine - necessary when you want to talk to the Kubernetes cluster from your local machine
* `Helm <https://helm.sh/docs/intro/quickstart/>`_: (super advanced) - our package manager for Kubernetes.  Necessary when you want to build helm packages on your local machine

All of the below examples are taken from the ``templates_and_examples`` folder of our Github repository!

Preparations for the development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Requirements:**

* Running version of the Kaapana platform and access to a terminal where the platform is running
* Installation of `Docker <https://docs.docker.com/get-docker/>`_ on your local machine
* Installation of `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_ (optional: convenient way to send images to the platform)

**Upload images to the platform**

* You have two options to upload images to the platform

   * Using that Data Upload: Create a zip file of images that end with .dcm and upload the images via drag&drop on the landing page in the section "Data upload"

   * Send images with dcmtk e.g.:

::

   dcmsend -v <ip-address of server> 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>

* Go to Meta on the landing page to check if the images were successfully uploaded
* In order to create a development environment to add new DAGs to the platform go to the extension section on the landing page and install the code-server-chart. Clicking on the link you will be served with a Visual Studio Code environment in the directory of Airflow, where you will find the Kaapana plugin (``workflows/plugins``), the data during processing (``workflows/data``), the models (``workflows/models``) and the directory for the DAGs definition (``workflows/dags``). 

In order to get a general idea about how to use the platform checkout TODO. Furthermore, it might be helpful to check out the TODO in order to get an idea of the concepts of the Kaapana platform.

