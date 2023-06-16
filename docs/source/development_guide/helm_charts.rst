.. _helm_charts:

Advanced: How Kaapana uses Helm
********************************

.. note::
      This section is **not** a necessary read in order to develop workflows or applications for Kaapana. It explains the technical details of how the platform uses Helm for managing extensions.
      


Helm is a package manager for Kubernetes that helps define and manage different Kubernetes applications. It simplifies the deployment process by providing a templating system for writing and maintaining YAML configuration files.

For a better understanding of how Helm works, it is recommended to read the `Helm documentation <https://helm.sh/docs/>`_.

To quickly get started with Helm, refer to the `Helm Quickstart Guide <https://helm.sh/docs/intro/quickstart/>`_. Note that the :term:`server-installation-script` uses snap to fetch the latest Helm version during installation.

For a detailed explanation of how to use templates in Helm, refer to `Helm Chart Template Guide <https://helm.sh/docs/chart_template_guide>`_.


How Kaapana uses Helm charts
==============================

Kaapana uses Helm to distribute and manage Kubernetes objects. Each service, DAG and extension is a requirement of the main **kaapana-admin-chart**. This chart contains the fundamental features of the platform such as reverse proxy, authentication, and extension management backend.

**kaapana-admin-chart** chart also contains **kaapana-platform-chart** as one of its requirements. Most of the interactive components of Kaapana is under **kaapana-platform-chart** , such as Airflow, PACS, Minio, landing page and Kaapana backend. The dependency tree below shows the complete structure.

Kaapana components have different folder structures based on their type:

1. A Kaapana :term:`extension` that can be installed/uninstalled via the Extensions tab:

.. code-block::

    jupyterlab
    │──── docker
          │──── Dockerfile
    │──── jupyterlab-chart
          │──── templates
                │──── deployment.yaml
          │──── Chart.yaml
          │──── values.yaml


2. A :term:`dag` (Directed Acyclic Graph) that defines a set of operators in Airflow:

.. code-block::

    dags
    │──── dag_collect_metadata.py


3. A Kaapana :term:`service` that provides main functionalities of the platform:

.. code-block::

    landing-page-kaapana
    │──── docker
    |     │──── Dockerfile
    │──── landing-page-kaapana-chart
          │──── templates
          |     │──── configmap.yaml
          |     │──── deployment.yaml
          |     │──── service.yaml
          │──── Chart.yaml
          │──── values.yaml   


.. note::

 Brief explanations of different YAML files:

 - **Chart.yaml** is the main configuration document for Helm charts. Details for the fields can be found in the `official documentation <https://helm.sh/docs/topics/charts/#the-chartyaml-file>`_.
    
 - **requirements.yaml** is used to define the required charts for the chart to work. Running :code:`helm dep up` creates a "deps" folder with the definition files of these charts.
    
 - **values.yaml** contains information that can be used in template files. Updating details in multiple Kubernetes objects becomes easier using `{{ .Values.fieldName }}` placeholders. More details on how to use values files can be found at `helm.sh <https://helm.sh/docs/chart_template_guide/values_files/>`_.


Useful Commands
===============

1. :code:`helm package .` packages a chart folder into a tgz file. This can be useful for uploading tgz files into the platform using the Upload component in Extensions tab

2. :code:`helm ls -A` lists all helm releases under all namespaces. This can be used to check whether every chart is deployed or not

3. :code:`helm ls --uninstalling --pending --failed` is useful to check whether any chart is stuck in an unwanted state. Use :code:`helm uninstall -n <namespace> --no-hooks <release-name>` to manually uninstall the release

4. :code:`helm get -n <namespace> <release-name>` prints the information as YAML files for all Kubernetes resources running under :code:`<release-name>` 


Chart Dependency Tree
======================

.. code-block::

    kaapana-admin-chart
    ├── admin-namespace
    ├── auth-backend-chart
    ├── cert-init-chart
    ├── kaapana-admin-chart-collections
    │   └── kaapana-extension-collection
    │       └── sub-charts
    │           ├── bodypartregression-workflow
    │           ├── code-server-chart
    │           ├── debug-container-chart
    │           ├── federated-setup-central-test-workflow
    │           ├── federated-setup-node-test-workflow
    │           ├── jupyterlab-chart
    │           ├── kaapana-persistence-chart
    │           ├── kaapana-platform-chart
    │           │   └── sub-charts
    │           │       ├── extensions-namespace
    │           │       ├── jobs-namespace
    │           │       ├── kaapana-library-chart
    │           │       └── services-namespace
    │           │           └── sub-charts
    │           │               ├── airflow-chart
    │           │               ├── alertmanager-chart
    │           │               ├── auth-backend-chart
    │           │               ├── cert-copy-chart
    │           │               ├── ctp-chart
    │           │               ├── dcm4chee-chart
    │           │               ├── dicom-init-chart
    │           │               ├── grafana-chart
    │           │               ├── kaapana-backend-chart
    │           │               ├── kaapana-plugin-chart
    │           │               ├── landing-page-kaapana-chart
    │           │               ├── meta-init-chart
    │           │               ├── minio-chart
    │           │               ├── minio-console-chart
    │           │               ├── minio-init-chart
    │           │               ├── node-exporter-chart
    │           │               ├── ohif-chart
    │           │               ├── ohif-chart-v3
    │           │               ├── opensearch-chart
    │           │               ├── os-dashboards-chart
    │           │               ├── prometheus-chart
    │           │               ├── static-website-chart
    │           ├── mhub-models-workflow
    │           ├── mitk-flow-chart
    │           ├── mitk-flow-workflow
    │           ├── mitk-workbench-chart
    │           ├── nnunet-federated-workflow
    │           ├── nnunet-workflow
    │           ├── radiomics-federated-workflow
    │           ├── radiomics-workflow
    │           ├── rateme-chart
    │           ├── rateme-workflow
    │           ├── shapemodel-workflow
    │           ├── slicer-workbench-chart
    │           ├── tensorboard-chart
    │           └── total-segmentator-workflow
    ├── kaapana-library-chart
    ├── keycloak-chart
    ├── keycloak-init-chart
    ├── kube-dashboard-chart
    ├── kube-helm-chart
    ├── maintenance-page-chart
    ├── nfs-server-chart
    ├── oAuth2-proxy-chart
    └── traefik-chart
