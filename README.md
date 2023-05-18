[![Documentation Status](https://readthedocs.org/projects/kaapana/badge/?version=latest)](https://kaapana.readthedocs.io/en/latest/?badge=latest)
<a href="https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ/"><img src="https://img.shields.io/badge/chat-slack-blueviolet" /></a>

## What is Kaapana?

Kaapana (from the hawaiian word kaʻāpana, meaning "distributor" or "part") is an open source toolkit for state of the art platform provisioning in the field of medical data analysis. The applications comprise  AI-based workflows and federated learning scenarios with a focus on radiological and radiotherapeutic imaging. 

Obtaining large amounts of medical data necessary for developing and training modern machine learning methods is an extremely challenging effort that often fails in a multi-center setting, e.g. due to technical, organizational and legal hurdles. A federated approach where the data remains under the authority of  the individual institutions and is only processed on-site is, in contrast, a promising approach ideally suited to overcome these difficulties.

Following this federated concept, the goal of Kaapana is to provide a framework and a set of tools for sharing data processing algorithms, for standardized workflow design and execution as well as for performing distributed method development. This will facilitate  data analysis in a compliant way enabling researchers and clinicians to perform large-scale multi-center studies.

By adhering to established standards and by adopting widely used open technologies for private cloud development and containerized data processing, Kaapana integrates seamlessly with the existing clinical IT infrastructure, such as the Picture Archiving and Communication System (PACS), and ensures modularity and easy extensibility.

Core components of Kaapana are:
* [dcm4chee](https://www.dcm4che.org/): open source PACS system serving as a central DICOM data storage in Kaapana
* [OpenSearch](https://opensearch.org/): search engine used to make the DICOM data searchable via their tags and meta information
* [OpenSearch Dashboards](https://opensearch.org/docs/latest/dashboards/index/): visualization dashboard enabling the interactive exploration of the DICOM data stored in Kaapana and indexed by OpenSearch
* [Airflow](https://airflow.apache.org/): workflow management system that enables complex and flexible data processing workflows in Kaapana via container chaining
* [Kubernetes](https://kubernetes.io/): Container orchestration
* [Keycloak](https://www.keycloak.org/): User authentication
* [Docker](https://www.docker.com/): container system to provide algorithms as well as the platform components itself

Kaapana is constantly developing and currently includes the following key-features:
* Large-scale image processing with SOTA deep learning algorithms, such as [nnU-Net](https://github.com/MIC-DKFZ/nnunet) image segmentation
* Analysing, evaluation and viewing of processed images and data
* Simple integration of new, customized algorithms and applications into the framework
* System monitoring
* User management

Currently the most widely used platform realized using Kaapana is the Joint Imaging Platform (JIP) of the German Cancer Consortium (DKTK). The [JIP](https://jip.dktk.dkfz.de/jiphomepage/) is currently being deployed at all 36 german university hospitals with the objective of distributed radiological image analysis and quantification.

For more information, please also take a look at our recent publication of the Kaapana-based [Joint Imaging Platform in JCO Clinical Cancer Informatics](https://ascopubs.org/doi/full/10.1200/CCI.20.00045).

## Documentation

Check out our [documentation](https://kaapana.readthedocs.io/en/latest/) for further information about Kaapana and how to use it!

## Versioning

As of Kaapana 0.2.0 we follow strict [SemVer](https://semver.org/) approach to versioning.

## Licence

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program (see file LICENCE).  
If not, see <https://www.gnu.org/licenses/>.

## Considerations on our license choice

You can use Kaapana to build any product you like, including commercial closed source ones since it is a highly modular system. Kaapana is licensed under the [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.en.html) for now since we want to ensure that we can integrate all developments and contributions to its core system for maximum benefit to the community and give everything back. We consider switching to a more liberal license in the future. This decision will depend on how our project develops and what the feedback from the community is regarding the license. 

Kaapana is built upon the great work of many other open source projects, see the documentation for details. For now we only release source code we created ourselves, since providing pre-built docker containers and licensing for highly modular container based systems is [a complex task](https://www.linuxfoundation.org/blog/2020/04/docker-containers-what-are-the-open-source-licensing-considerations/). We have done our very best to fulfil all requirements, and the choice of AGPL was motivated mainly to make sure we can improve and advance Kaapana in the best way for the whole community. If you have thoughts about this or if you disagree with our way using a particular third-party toolkit or miss something please let us know and get in touch. We are open for any feedback and advice on this challenging topic.

## Acknowledgments

### Supporting projects

**Building Data Rich Clinical Trials - CCE_DART**: This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 965397. Website: <https://cce-dart.com/>

**Capturing Tumor Heterogeneity in Hepatocellular Carcinoma - A Radiomics Approach Systematically Tested in Transgenic Mice** This project is partially funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) – 410981386. Website: <https://gepris.dfg.de/gepris/projekt/410981386>

**Data Science Driven Surgical Oncology Project**: This work was partially supported by the Data Science Driven Surgical Oncology Project (DSdSO), funded by the Surgical Oncology Program at the National Center for Tumor Diseases (NCT), Heidelberg, a partnership by DKFZ, UKHD, Heidelberg University. Website: <https://www.nct-heidelberg.de/forschung/precision-local-therapy-and-image-guidance/surgical-oncology.html>

**Joint Imaging Platform**: This work was partially supported by Joint Imaging Platform, funded by the German Cancer Consortium. Website: <https://jip.dktk.dkfz.de/jiphomepage/>

**HiGHmed**: This work was partially supported by the HiGHmed Consortium, funded by the German Federal Ministry of Education and Research (BMBF, funding code 01ZZ1802A)). Website: <https://highmed.org/>

**RACOON**: This work was partially supported by RACOON, funded by the German Federal Ministry of Education and ResearchDieses in the Netzwerk Universitätsmedizin (NUM; funding code 01KX2021). Website: <https://www.netzwerk-universitaetsmedizin.de/projekte/racoon>

**Trustworthy Federated Data Analysis - TFDA**: This work is partially funded by the Helmholtz Association within the project "Trustworthy Federated Data Analytics” (TFDA) (funding number
ZT-I-OO1 4). Website: <https://tfda.hmsp.center/>

Copyright (C) 2020  German Cancer Research Center (DKFZ)
