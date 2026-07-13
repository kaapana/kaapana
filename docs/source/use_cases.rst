.. _use_cases:

Use Cases
#########

Kaapana is a toolkit. Any containerized algorithm or application can be added as an
extension, so the platform adapts to a given research question. Data,
processing tools, interactive workspaces and access control are available
through a single login. The use cases below describe how Kaapana has been
used in practice; they are not a complete list of possible applications.

Analysis at scale
------------------

**End-to-end integrated medical image analysis**: ingest, curate, process,
analyze and review large scale data in a single interface. External PACS
integration or DICOM upload for ingestion, the datasets view for curation,
Workflows for processing, and OHIF / MITK / Slicer viewers to review. All
steps are scoped by projects.

**Automated segmentation at scale**: trigger the TotalSegmentator or nnUNet
workflow on a whole dataset selected in the datasets view; results land back
as DICOM SEG.

**Digital pathology / whole-slide imaging**: ingest pathology images via the
wsiconv workflow (converts whole-slide images to DICOM). Review them in the
SLIM viewer, with histopathology thumbnails generated automatically for the
datasets view.

**Quantitative imaging biomarkers**: extract shape, intensity and texture
biomarkers from segmented images with the radiomics workflow (PyRadiomics),
storing results as CSV, JSON or XML. Correlate your findings with additional data using the interactive analysis environments (JupyterLab) and present the results in easily accessible reports.

Collaborative, multi-centre research
--------------------------------------

**Federated learning across sites**: train models without moving patient
data. The nnU-Net federated workflow trains across all participating sites
automatically; training curves are available in TensorBoard.
A study using nnU-Net federated in Kaapana was published in the RACOON
network: https://pubmed.ncbi.nlm.nih.gov/39455061/

**Federated quantitative analysis without pooling**: analyze locally,
aggregate only results. The radiomics-federated workflow runs PyRadiomics at
each site and returns aggregated features, not raw images.

**Sharing methods across sites**: publish a workflow extension to an
OCI-based extension registry and pull it at another site, so a workflow
built once can be installed and run elsewhere.

Multi-centre disease-specific studies
----------------------------------------

Imaging data from many centres is pooled into one large, central Kaapana
instance, and the study runs on the combined cohort. This is how the RACOON
network runs its disease-specific studies.

**Disease-specific imaging studies on a pooled cohort**: curate the cohort
in the datasets view, run segmentation workflows (nnU-Net / TotalSegmentator)
together with PyRadiomics for characterization, and review results in the
OHIF viewer, MITK Workbench or 3D Slicer. Each study stays isolated from the
others through the project and user separation feature.
Examples from the RACOON network: AI-assisted prostate cancer detection on
MRI (Prostate), a nationwide thoracic imaging atlas (COMBINE),
neuroradiological diagnosis and monitoring (BRAIN), early detection of
adenomyosis (FADEN), pulmonary embolism diagnosis and risk stratification
(CORE-PE), and paediatric non-Hodgkin lymphoma staging with image-based
biomarkers (RESCUE).

Data management, review & platform
--------------------------------------

**Live scientific / research imaging database**: run a central, always-on
database which researchers can work against daily, as in the case of
DKFZ's scientific database wDB, currently hosting ~400,000 series. The
database is built on the integrated PACS (dcm4chee), the OpenSearch
metadata index and the MinIO object store, and is explored through the
datasets view.

**Cohort building, curation & metadata exploration**: filter, tag and
visualize DICOM images by metadata in the datasets view to carve out study
cohorts. Use built-in tools like JupyterLab for ad-hoc querying and
scripting against the data, and Collabora, a LibreOffice-based office suite,
for collaborative documents, spreadsheets and presentations alongside it.

.. TODO Philipp Fine-Tuning + Training Loop Paper

**Model Management and Model Fine-Tuning**:
https://pubs.rsna.org/doi/10.1148/ryai.250200

Governance, extensibility & building your own
--------------------------------------------------

**Multi-tenant, project-based data governance**: run many studies and teams
on one platform, separated via the project separation feature (backed by
Keycloak and Open Policy Agent), which isolates data, workflows and access
per project.

**Build your own platform on Kaapana**: Kaapana is open source, released
under the AGPLv3 license. Institutions deploy their own Kaapana-based
platform for their networks, like RACOON, CCE-DART, or UNCAN.

**Extensibility**: algorithms can be added through the extensions
mechanism, custom workflows can be plugged in, and new custom applications
(e.g. another viewer or tool) can be shipped into the platform. Development
and deployment can happen interactively inside the platform with the
integrated VSCode Server and Extension Development Kit (EDK).

.. TODO Philipp: Run it on premis transfer to the cloud
