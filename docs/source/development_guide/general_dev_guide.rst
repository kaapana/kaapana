.. _general_dev_guide:

Introduction
------------

This guide is intended to provide a quick and easy way to get started with developments on the Kaapana platform.
 
The guide currently consists of three parts. This part gives a brief overview over the technologies and needed preparations for the rest of the guide.
The part :ref:`workflow_dev_guide` focuses on the integration of custom processing workflows into the platform. 
It will be explained how to formulate workflows in Airflow-DAGs and further how to integrate workflows as extensions into the Kaapana technology stack.
The last section :ref:`application_dev_guide` gives step by step instructions how to deploy a general--purpose web application within Kaapana as an example how new components can be added to the platform.


List of the technologies
^^^^^^^^^^^^^^^^^^^^^^^^
These tutorials/technologies are good references, when starting with the Kaapana deployment:

* `Docker <https://docs.docker.com/get-docker/>`_: Necessary when you want to build containers on your local machine
* `Airflow <https://airflow.apache.org/docs/stable/>`_: Our pipeline tool for processing algorithms
* `Kubernetes <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`_: (Advanced) On your local machine - necessary when you want to talk to the Kubernetes cluster from your local machine
* `Helm <https://helm.sh/docs/intro/quickstart/>`_: (super advanced) - our package manager for Kubernetes.  Necessary when you want to build helm packages on your local machine

All of the examples below are taken from the ``templates_and_examples`` folder of our Github repository!

Requirements
^^^^^^^^^^^^

* Running version of the Kaapana platform and access to a terminal where the platform is running
* Installation of `Docker <https://docs.docker.com/get-docker/>`_ on your local machine
* optional: Installation of `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_ to send images to the platform, but you can also use the Data Upload tool of the Kaapana platform

**Upload images to the platform**

There are two options how to upload images to the platform

   * Zip the DICOM or Nifti images which you want to upload to the platform in a .zip-folder and drag&drop the zipped folder in the Data Upload tool

   * Send images with dcmtk e.g.:

::

   dcmsend -v <ip-address-of-server> <dicom port, default:11112> --scan-directories --call <dataset-name> --scan-pattern '*.dcm' --recurse <data-dir-of-DICOM-images>

To check whether the data was sucessfully uploaded to the platform, navigate to Workflows -> Datasets and you will find your data!

**Note**

In order to get a general idea about how to use the platform and to get an idea about its individual parts checkout the :ref:`user_guide`.
