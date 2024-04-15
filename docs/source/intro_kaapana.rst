
.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/img/kaapana_logo_2.png
   :alt: Kaapana logo
   :class: logo
   :align: center


.. raw:: html

    <br />
    <br />
    <br />

.. _about_kaapana:


What is Kaapana?
================

Kaapana (from the hawaiian word kaʻāpana, meaning "distributor" or "part") is an open source toolkit for state of the art platform provisioning in the field of medical data analysis. The applications comprise  AI-based workflows and federated learning scenarios with a focus on radiological and radiotherapeutic imaging. 

Obtaining large amounts of medical data necessary for developing and training modern machine learning methods is an extremely challenging effort that often fails in a multi-center setting, e.g. due to technical, organizational and legal hurdles. A federated approach where the data remains under the authority of  the individual institutions and is only processed on-site is, in contrast, a promising approach ideally suited to overcome these difficulties.

Following this federated concept, the goal of Kaapana is to provide a framework and a set of tools for sharing data processing algorithms, for standardized workflow design and execution as well as for performing distributed method development. This will facilitate  data analysis in a compliant way enabling researchers and clinicians to perform large-scale multi-center studies.

By adhering to established standards and by adopting widely used open technologies for private cloud development and containerized data processing, Kaapana integrates seamlessly with the existing clinical IT infrastructure, such as the Picture Archiving and Communication System (PACS), and ensures modularity and easy extensibility.


.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/kaapana-v0.2.1-showcase-fps30-1920p.gif
   :alt: Kaapana v0.2.1


Core components of Kaapana:

* :ref:`wms_start`: Large-scale image processing with SOTA deep learning algorithms, such as `nnU-Net <https://github.com/MIC-DKFZ/nnunet>`_ image segmentation and `TotalSegmentator <https://github.com/wasserth/TotalSegmentator>`_
* :ref:`datasets`: Exploration, visualization and curation of medical images
* :ref:`extensions`: Simple integration of new, customized algorithms and applications
* :ref:`store`: An integrated PACS system and Minio for other types of data
* :ref:`monitoring`: Extensive resource and system monitoring for administrators
* :ref:`keycloak`: Simple user management via `Keycloak <https://www.keycloak.org/>`_

Core technologies used in Kaapana:

* `Kubernetes <https://kubernetes.io/>`_: Container orchestration system
* `Airflow <https://airflow.apache.org/>`_: Workflow management system enabling complex and flexible data processing workflows
* `OpenSearch <https://opensearch.org/>`_: Search engine for DICOM metadata based searches
* `dcm4chee <https://www.dcm4che.org/>`_: Open source PACS system serving as a central DICOM data storage
* `Prometheus <https://github.com/prometheus/prometheus>`_: Collecting metrics for system monitoring
* `Grafana <https://github.com/grafana/grafana>`_: Visualization for monitoring metrics
* `Keycloak <https://www.keycloak.org/>`_: User authentication

Currently the most widely used platform realized using Kaapana is the Joint Imaging Platform (JIP) of the German Cancer Consortium (DKTK). The `JIP <https://jip.dktk.dkfz.de/jiphomepage/>`_ is currently being deployed at all 36 german university hospitals with the objective of distributed radiological image analysis and quantification.

For more information, please also take a look at our recent publication of the Kaapana-based `Joint Imaging Platform in JCO Clinical Cancer Informatics <https://ascopubs.org/doi/full/10.1200/CCI.20.00045>`_.



.. raw:: html

   <style>
   .logo {
       width: 30%;
   }
   </style>