.. _kaapana_doc:

Mission Statement
#################
TODO 


.. _kaapana_concept:

Concept
#######

Requirements
------------
You should hava a basic understanding of:

1. `Docker <https://docker-curriculum.com/>`__
2. `Kubernetes <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`__
3. `Helm <https://helm.sh/>`__


What is a build of Kaapana?
---------------------------
Unlike classical software projects, Kaapana is not a monolithic software, 
which consists of source code of a single programming language and is compiled into a binary.
This toolkit consists of many individual components, which are all built individually in form of :term:`docker` :term:`container<docker>` and then provided on demand via a registry.
In the future we will also offer the possibility to build the platform without an additional Docker :term:`registry` - but at this point in time this is still necessary.
The easiest solution is to use `Dockerhub <https://hub.docker.com/>`__, which offers a free registry. (Disadvantage: all own containers are publicly accessible).
If you want to run your own private registry we recommend `Harbor <https://goharbor.io/>`__ or `Artifactory <https://jfrog.com/artifactory/>`__ as a professional solution.

In addition to the docker containers of the services, a build also consists of the associated :term:`service` package-definitions in form of :term:`helm` :term:`chart`.
The simplest way to think of Helm is as a package manager, which allows the management of dependencies, installations, updates etc. for all services and the platform itself.

Since Dockerhub currently offers no possibility to manage helm charts, we have made our registry publicly accessible.
So it is possible to get the charts for the "Kaapana-platform" directly from `our registry <https://dktk-jip-registry.dkfz.de/>`__.
In principle, Helm Charts can also be used locally without an external registry, as they are just zip-files.

Basic deployment schema:

.. mermaid::

   graph LR
      A[Registry] --> B[Helm Chart]
      B -->|deployment| C{Kubernetes}
      A --> |Docker Container| C
      C --> D[PACS]
      C --> E[Viewer]
      C --> F[Airflow]
      C --> G[...]




Technology-stack
################

.. figure:: _static/img/technology_stack.png
   :align: center
   :scale: 25 %



Basic structure of the repository
#################################

The platform is running on servers, which are operated locally at each of the participating sites.
More precisely, the software is a collection of components that are linked together using modern cloud technologies.
This also reflects the platform character, as these components can be easily extended, adapted and exchanged.
The underlying technology is `Docker <https://opensource.com/resources/what-docker>`__. All components and
processing methods are running inside their own container, which brings a lot of benefits.
All containers are then glued together by the container orchestration tool
`Kubernetes <https://kubernetes.io/docs/concepts/overview/what-is-kubernetes/>`__.
This stack of technologies proofed to be very powerful and is widely used as state of the art "datacenter operation system".
We will not go into detail on these topics, as there is already a lot of information online available.

In order to ensure a better overview, we have divided all components into six areas:

- **Base**
- **Store**
- **Meta**
- **Flow**
- **Monitoring**
- **System**

The following sections give a basic overview of each of these areas and describe them.

Platform structure
##################

Base
----
The base section represents the main user interface of the Kaapana.
It is basically a website which combines the interfaces of all components in a single view.

Store
-----
The Store is responsible for data storage.
The main component is a fully-fledged opensource PACS (`DCM4CHEE <https://www.dcm4che.org/>`__).
There is also a object-store (`Minio <https://www.minio.io/>`__), which will be used to store non DICOM data.
This will also enable the provision of download-links for cohort data and experiment results.
A web-based DICOM viewer (`OHIF <http://ohif.org/>`__) has been integrated to show images in the browser.
The functionality of this viewer is limited at the moment, but more features will come soon.

.. raw:: latex

    \clearpage

Meta
----
Meta makes it possible to visualize and explore the metadata of images.
It allows not only an overview of the data on the system, but is also used to define cohorts for experiments.
By creating filters for desired DICOM tags, the total data set can be stratified.
In addition, the results can be combined with visually appealing graphs in dashboards. 
It is also possible to create your own visualizations and dashboards.
For this functionality mainly two frameworks are used:

- `Elasticsearch <https://medium.com/@victorsmelopoa/an-introduction-to-elasticsearch-with-kibana-78071db3704>`__ as database and search engine for metadata
- `Kibana <https://www.elastic.co/guide/en/kibana/current/introduction.html>`__ for the visualizations and filters

In order to get a basic understanding of visualizations and dashboards,
existing documentation from Kibana can be used.

.. raw:: latex

    \clearpage

Flow
----

.. figure:: _static/img/flow_figure.png
   :align: center
   :scale: 20 %

Flow contains all components related to processing.
The main component is the workflow engine, which was developed on the basis of `Airflow <https://airflow.apache.org/>`__.
It allows to define pipelines which will execute the algorithms.
Like all other components, processing steps consist of docker containers, which are lined up to achieve
the desired result.

Example of a typical workflow:


.. figure:: _static/img/dag_example.png
   :align: center
   :scale: 40 %

All processing containers are also handled by Kubernetes.
This will ensure a completely integrated processing unit.

Since this topic is very extensive and important for the usage of the Kaapana,
we will dedicate it a separate chapter in this documentation.
The development guide explains the basic principles and gives an introductory example.

It is also important to note that this is **currently work in progress**.
There will be constant updates for both, the documentation, and the framework itself.
Therefore you should use the online documentation to get the latest version.

In addition to the workflow engine, there are also components which are responsible for
the distribution and acceptance of images within the platform. Most importantly, there is the
`Clinical Trial Processor (CTP) <https://mircwiki.rsna.org/index.php?title=MIRC_CTP>`__.
It will open port 11112 on the server to accept DICOM images directly from your clinic PACS.
The rest of the image handling (metadata extraction, PACS storage etc.) will be done automatically by an predefined worflow.

.. raw:: latex

    \clearpage

Monitoring
----------

As with all platforms, a system to monitor the current system status is needed.
To provide this, the Kaapana utilized a commonly used combination of `Prometheus <https://prometheus.io/>`__ and `Grafana <https://grafana.com/>`__.
The graphical dashboards present states such as disk space, CPU and memory usage, network pressure etc.

.. figure:: _static/img/grafana.png
   :align: center
   :scale: 20 %

For the monitoring of the system components, there is a powerfull Kubernetes dashboard,
which enables all kinds of container monitoring and system adjustment.

.. figure:: _static/img/kube_dashboard.png
   :align: center
   :scale: 25 %

System
------
This category includes many functionalities, which are needed as a basis for the system.
Most of them are Kubernetes/network related and therefore left out here.
The only important system to note is `Keycloak <https://www.keycloak.org/>`__, which is used as a identity provider.
The system uses `OpenID Connect <https://openid.net/connect/>`__ as authentication system.
This enables simple user management and the integration of existing LDAP and Kerberos systems.
So you should be able to use the existing user accounts of the hospital infrastructure.

