.. _what_is_kaapana:

What is Kaapana?
=================================
Kaapana (from the hawaiian word kaʻāpana, meaning “distributor” or “part”) is an open source toolkit for state of the art platform provisioning in the field of medical data analysis. The applications comprise  AI-based workflows and federated learning scenarios with a focus on radiological and radiotherapeutic imaging. 

Obtaining large amounts of medical data necessary for developing and training modern machine learning methods is an extremely challenging effort that often fails in a multi-center setting, e.g. due to technical, organizational and legal hurdles. A federated approach where the data remains under the authority of  the individual institutions and is only processed on-site is, in contrast, a promising approach ideally suited to overcome these difficulties.

Following this federated concept, the goal of Kaapana is to provide a framework and a set of tools for sharing data processing algorithms, for standardized workflow design and execution as well as for performing distributed method development. This will facilitate  data analysis in a compliant way enabling researchers and clinicians to perform large-scale multi-center studies.

By adhering to established standards and by adopting widely used open technologies for private cloud development and containerized data processing, Kaapana integrates seamlessly with the existing clinical IT infrastructure, such as the Picture Archiving and Communication System (PACS), and ensures modularity and easy extensibility.


Core components of Kaapana are:

- dcm4chee_: open source PACS system serving as a central DICOM data storage in Kaapana
- Elasticsearch_: search engine used to make the DICOM data searchable via their tags and meta information
- Kibana_: visualization dashboard enabling the interactive exploration of the DICOM data stored in Kaapana and indexed by Elasticsearch
- Airflow_: workflow management system that enables complex and flexible data processing workflows in Kaapana via container chaining
- Kubernetes_: container orchestration
- Keycloak_: user authentication

- Docker_: container system to provide algorithms as well as the platform components itself

Kaapana is constantly developing and currently includes the following key-features:

- Large-scale image processing with SOTA deep learning algorithms, such as nnU-Net_ image segmentation 
- Analysing, evaluation and viewing of processed images and data
- Simple integration of new, customized algorithms and applications into the framework
- System monitoring

- User management

Currently the most widely used platform realized using Kaapana is the Joint Imaging Platform (JIP_) of the German Cancer Consortium (DKTK). The JIP  is currently being deployed at all 36 german university hospitals with the objective of distributed radiological image analysis and quantification.

For more information, please also take a look at our recent publication of the Kaapana-based Joint Imaging Platform in JCO Clinical Cancer Informatics (JCO_).

.. _dcm4chee: https://www.dcm4che.org/
.. _Elasticsearch: https://www.elastic.co/de/elasticsearch/
.. _Kibana: https://www.elastic.co/de/kibana/
.. _Airflow: https://airflow.apache.org/
.. _Kubernetes: https://kubernetes.io/
.. _Keycloak: https://www.keycloak.org/
.. _Docker: https://www.docker.com/
.. _nnU-Net: https://github.com/MIC-DKFZ/nnunet
.. _JIP: https://jip.dktk.dkfz.de/jiphomepage/
.._JCO: https://ascopubs.org/doi/pdf/10.1200/CCI.20.00045
