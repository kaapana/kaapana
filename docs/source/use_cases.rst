.. _use_cases:

Use Cases
#########

**Kaapana is a collection of specialized tools and services, not a fixed application.** It enables the creation of specialized platforms tailored to specific use cases such as large-scale medical image analysis, collaborative research, multi-center studies, and more.

In Kaapana, any analysis method, research tool or service can be containerized and added as an extension, creating a flexible platform that adapts to your specific research question rather than requiring your research to adapt to the platform.

Kaapana provides the core capabilities required for medical imaging research within a single platform, including large-scale data processing, data curation, interactive workspaces, secure access through a single sign-on, and tools for collaboration. By bringing these components together, Kaapana allows researchers to focus on their scientific work rather than assembling and maintaining the underlying infrastructure.

The following use cases provide real-world examples of how Kaapana is used, they are an inspiration not a complete list by any means as Kaapana is very flexible to adapt to your specific needs.


Analysis at scale
------------------

**End-to-end integrated medical image analysis**: Kaapana enables users to ingest, curate, process, analyze, and review large medical imaging datasets within a single, unified interface. Data can be uploaded through the web frontend. Alternatively, Kaapana can be integrated into existing imaging infrastructure by acting as a DICOM node or by communicating directly with external PACS systems. Ingested data can be curated in the dataset view and reviewed or annotated using integrated tools such as OHIF, MITK, 3D Slicer, and the SLIM Viewer. The platform provides analysis workflows for automated segmentation, model training, and radiomics, and can be extended through the app store. All activities are organized within projects, allowing a single Kaapana instance to support multiple teams, use cases, or organizational settings.

**Automated segmentation at scale**: use state-of-the-art methods for automatic segmentation, such as TotalSegmentator and nnU-Net. Run the corresponding workflows directly from the dataset view to generate DICOM Segmentation objects. With the available fine-tuning and training workflows, new nnU-Net models can be trained on local data.

**Digital pathology / whole-slide imaging**: ingest pathology images using the wsiconv workflow, which converts whole-slide images to DICOM. Review them in the SLIM Viewer, OHIF, or at scale in the dataset view as histopathology thumbnails are generated automatically for the dataset view.

**Biomarker discovery**: use automatic segmentation methods to segment relevant structures in images and extract radiomics signatures using either hand-crafted radiomics features or deep-learning-based models. Correlate your findings with additional data using the interactive analysis environments (RStudio and JupyterLab) and present the results in easily accessible reports.


Collaborative, multi-center research
--------------------------------------

**Federated learning across sites**: train models without moving patient data. Use the federated nnU-Net workflow to train models across multiple nodes. Orchestration is handled through Airflow DAGs, while the platform's federated operators coordinate the training rounds across sites. Monitor training curves in TensorBoard. (Examples: `Published Study in RACOON Network <https://pubmed.ncbi.nlm.nih.gov/39455061/>`_, UNCAN)

**Federated quantitative analysis without pooling**: analyze locally, aggregate only results. The radiomics-federated workflow runs PyRadiomics at each site and returns aggregated features rather than raw images. The same DAG-based federation is applied to analysis instead of training.

**Method sharing**: wrapping a method, algorithm, or tool as a Kaapana extension enables it to be installed and used easily in other Kaapana instances. In large research consortia, technical partners can focus on method development, while Kaapana handles deployment and integration into site-specific infrastructure. (Examples: CCE_DART, RACOON)


Multi-center disease-specific studies
----------------------------------------

Instead of keeping data at each site, imaging data from many centers is collected into one large, central Kaapana instance and the study runs there on the combined cohort. This is for example how the RACOON network runs its disease-specific studies.

**Disease-specific imaging studies on a pooled cohort**: curate the cohort in the datasets view, run segmentation workflows (nnU-Net / TotalSegmentator) together with PyRadiomics for characterization, and review results in the OHIF viewer, MITK Workbench or 3D Slicer. Each study stays isolated from the others through the project and user separation feature.
Examples from the RACOON network: AI-assisted prostate cancer detection on MRI (Prostate), a nationwide thoracic imaging atlas (COMBINE), neuroradiological diagnosis and monitoring (BRAIN), early detection of adenomyosis (FADEN), pulmonary embolism diagnosis and risk stratification (CORE-PE), and pediatric non-Hodgkin lymphoma staging with image-based biomarkers (RESCUE).


Data management, review & platform
--------------------------------------

**Scientific imaging research database**: straightforward integration into DICOM-based infrastructures, a robust backend, and scalable data-curation tools accessible through a user-friendly web frontend make Kaapana well suited for use as a central research imaging database. One example is the Wissenschaftliche Datenbank (wDB) at the German Cancer Research Center (DKFZ).

**Cohort building, curation & metadata exploration**: filter, tag and visualize large volumes of DICOM data based on metadata in the datasets view to carve out study cohorts. Use built-in tools like JupyterLab for ad-hoc querying and scripting against the data, as well as Collabora for collaborative spreadsheets and reports.

**Model management and model fine-tuning**: segmentation models can be trained from scratch, while existing models can be fine-tuned using local data. This provides the foundation for efficient, iterative training cycles that continuously improve model performance while minimizing the required annotation effort (`Example study in RACOON <https://pubs.rsna.org/doi/10.1148/ryai.250200>`_)


Governance, extensibility & building your own
--------------------------------------------------

**Multi-tenant, project-based data governance**: run many studies and teams in one platform, cleanly separated via the project separation feature (backed by Keycloak and Open Policy Agent), which isolates data, workflows, and access per project.

**Open Source and Open Science**: Kaapana is licensed under the GNU Affero General Public License v3.0, making the platform openly available to the research community. As adoption grows across research projects and institutions, we aim to foster a collaborative community that shares methods, workflows, and tools while advancing the principles of open science.

**On-premises or in the cloud**: Kaapana supports a wide range of deployment environments, from a single virtual machine or multi-VM setup to local Kubernetes clusters and public cloud platforms. This flexibility enables Kaapana to integrate into the heterogeneous IT infrastructures commonly found in research institutions, whether you prefer to operate the platform on your own hardware or deploy it using cloud resources.

**Build your own platforms**: Kaapana is built on Kubernetes and a microservice architecture, allowing it to be adapted to a wide range of deployment scenarios. Use the complete feature set to create a comprehensive imaging and AI platform for your research group or institution, or remove unnecessary components to build a lightweight web-based showcase for your AI methods.

.. TODO link to neurrad

**Extend the platform to meet your needs**: Add algorithms through the extensions mechanism, plug in a custom workflow, or ship a new custom application (e.g. another viewer or tool) into the platform. Develop and deploy interactively inside the platform with the integrated VS Code Server and Extension Development Kit (EDK).
