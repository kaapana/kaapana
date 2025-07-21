.. _general_dev_guide:

Introduction
------------

This guide is intended to provide a quick and easy way to get started with developing, deploying and running custom extensions for Kaapana.
 
It consists of three parts. This part gives a brief overview over the technologies and needed preparations for the rest of the guide.
The part :ref:`workflow_dev_guide` focuses on the integration of custom processing workflows into the platform. These can be as simple as collecting metadata from DICOM images or as complex as a full-fledged machine learning pipeline.
This section explains how to write Airflow-DAGs and how to integrate custom workflows as extensions into the Kaapana technology stack.
The last section :ref:`application_dev_guide` provides instructions on deploying a general-purpose web application inside Kaapana.

.. important::
   The reader should be familiar with basic concepts of the Kaapana platform. If you are not, please refer to the :ref:`user_guide` for a general introduction to the concept of the platform and its components.

Terminology
^^^^^^^^^^^
List of Kaapana specific terms used in this guide. Note that the reader is also expected to know about containers, images and registries, which are not explained here.

* **Extension**: A component that can be installed and run on the Kaapana platform. List of stable extensions can be found in the :ref:`extensions` section of the documentation.
* **Application Extension**: These extensions deploy standalone web applications, usually accessible via subpaths in the platform (e.g. JupyterLab, MITKWorkbench)
* **Workflow Extension**: These extensions deploy workflows, which are executed via Airflow. Every processing pipeline inside Kaapana is considered a workflow (e.g. nnunet-training, totalsegmentator, collect-metadata)
* **DAG**: Airflow Directed Acyclic Graph, defines a collection of operators that are executed in a specific order. Every workflow inside Kaapana defines a DAG that is managed by Airflow.
* **Operator**: A single task inside a DAG. Kaapana utilizes distributed operators, where each operator is linked to a specific container that is executed in a Kubernetes pod. The scheduler of Airflow is responsible for executing the operators in the correct order.
* **Chart**: A Kaapana extension is technically a Helm package which contains its configuration. It references the container images of the extension, and defines the necessary Kubernetes resources around them.
* **Microk8s**: Kubernetes distribution used in Kaapana. It contains the container runtime called :code:`containerd`, abbreviated as :code:`ctr`, which is used to run containers inside the platform.
* **EDK**: Extension Development Kit, available for versions >= 0.4.0. It provides a development environment inside Kaapana for building and deploying containers and charts. For more information :ref:`extensions_edk`


List of Technologies
^^^^^^^^^^^^^^^^^^^^
The following technologies will be referenced throughout the guide:

* `Docker <https://docs.docker.com/get-docker/>`_ or `Podman <https://podman.io/>`_: Necessary for building containers on a local machine
* `Airflow <https://airflow.apache.org/docs/stable/>`_: Workflow management system used in Kaapana
* `Kubernetes <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`_: Container orchestration system, every component in Kaapana is inside a Kubernetes cluster. We deploy the platform with `microk8s <https://microk8s.io/docs/getting-started>`_ .
* `Helm <https://helm.sh/docs/intro/quickstart/>`_: Package manager for Kubernetes. Necessary when you want to build helm packages on your local machine

