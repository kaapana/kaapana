.. _what_is_kaapana:

# What is :term:`Kaapana`?

Kaapana (from the hawaiian word kaʻāpana, meaning “distributor” or “part”) is an open source toolkit for creating federated medical data analysis and quantification platforms, with a focus on radiological and radiotherapeutic imaging. 

Obtaining the large amounts of medical data necessary for developing and training modern methods for big data processing by extracting it from their individual institutions is an extremely challenging effort that often fails, e.g. due to technical, organizational and legal hurdles. A federated approach where the data remains in the respective institution and is processed on-site is in contrast a very promising approach ideally suited for such a scenario. 

Following this federated concept, the goal of Kaapana is to provide a framework and a set of tools for sharing data processing algorithms, for standardized workflow design and execution as well as for performing distributed method development and data analysis in a compliant way that will enable researchers and clinicians to perform large-scale multi-center studies.

By adhering to established standards and by adopting widely used open technologies for private cloud development and containerized data processing, Kaapana integrates seamlessly with the existing clinical IT infrastructure, such as the Picture Archiving and Communication System (PACS), and ensures modularity and easy extensibility.

Core container components of Kaapana are:
* [dcm4chee](https://www.dcm4che.org/): open source PACS system serving as a central DICOM data storage in Kaapana
* [Elasticsearch](https://www.elastic.co/de/elasticsearch/): search engine used to make the DICOM data searchable via their tags
* [Kibana](https://www.elastic.co/de/kibana/): visualization dashboard enabling the interactive exploration of the DICOM data stored in Kaapana based on the Elasticsearch
* [Airflow](https://airflow.apache.org/): workflow management system that enables complex and flexible data processing workflows in Kaapana

Kaapana is constantly developing and currently includes the following key-features:
* Large-scale image processing with SOTA deep learning algorithms, such as [nnU-Net](https://github.com/MIC-DKFZ/nnunet) image segmentation 
* Analysing, evaluation and viewing of processed images and data
* Simple integration of new, customized algorithms and applications into the framework

Currently the most widely used platform realized using Kaapana is the Joint Imaging Platform (JIP) of the German Cancer Consortium (DKTK) which is currently being deployed at all 36 german university hospitals with the objective of distributed radiological image analysis and quantification.

For a more information, please also take a look at our recent publication of the Kaapana-based Joint Imaging Platform in JCO Clinical Cancer Informatics (LINK HERE).
