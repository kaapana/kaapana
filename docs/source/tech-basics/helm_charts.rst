.. _helm_charts:

What is Helm
************

Helm is a package manager for Kubernetes, it helps to define and manage different Kubernetes applications. It is also useful for writing and maintaining YAML configuration files via templating.

`Helm <https://helm.sh/docs/>`_ has a great documentation and it is definitely a recommended read for a deeper understanding.

`Helm quickstart <https://helm.sh/docs/intro/quickstart/>`_ provides a fast introduction to main concepts in Helm. For the installation part, note that the :term:`server-installation-script` uses snap to fetch the most recent Helm version available.

For a detailed explanation of how to use templates in Helm refer to `helm docs <https://helm.sh/docs/chart_template_guide>`_ .



How Kaapana uses Helm charts
==============================

Kaapana uses Helm to distribute and manage the Kubernetes objects. Every service, DAG and Extension is a requirement of the main **kaapana-platform-chart**. A full dependency tree can be found below.

Every Kaapana service consists of two folders, one for the container image document (usually a Dockerfile) and related development files, the other for the Helm chart that deploys this container into the Kubernetes cluster.

Here are some example folder structures for different types of Kaapana components:

**1.** A Kaapana :term:`extension` that can be installed/uninstalled explicitly via the Extensions tab

.. code-block::

    jupyterlab
    │──── docker
          │──── Dockerfile
    │──── jupyterlab-chart
          │──── templates
                │──── deployment.yaml
          │──── Chart.yaml
          │──── values.yaml


**2.** A :term:`dag` that defines a set of operators in Airflow

.. code-block::

    dags
    │──── dag_collect_metadata.py


**3.** A Kaapana :term:`service` that provides main functionalities of the platform

.. code-block::

    landing-page-kaapana
    │──── docker
    |     │────Dockerfile
    │──── landing-page-kaapana-chart
          │──── templates
          |     │──── configmap.yaml
          |     │──── deployment.yaml
          |     │──── service.yaml
          │──── Chart.yaml
          │──── values.yaml   


.. note::

 Some brief explanations of different yaml files
    
 - **Chart.yaml** is the main configuration document for Helm charts. Details for the fields can be found in `official documentation <https://helm.sh/docs/topics/charts/#the-chartyaml-file>`_ .
    
 - **requirements.yaml** is used for defining the required charts for the chart to work. Running :code:`helm dep up` creates a deps folder with the definition files of these charts
    
 - **values.yaml** contains the information that can be used in template files. This makes updating the details in multiple Kubernetes objects easier via using `{{ .Values.fieldName }}` placeholder. More details on how to use values files can be found at `helm.sh <https://helm.sh/docs/chart_template_guide/values_files/>`_ .



Chart dependency tree
======================

.. code-block::

    kaapana-platform-chart
    │──── kibana-kaapana-chart
    │──── meta-init-chart
    │──── elasticsearch-chart
    │──── landing-page-kaapana-chart
    │──── kaapana-core-chart
        │──── error-pages-chart
        │──── oAuth2-proxy-chart
        │──── keycloak-chart
        │──── traefik-chart
        │──── kube-dashboard-chart
        │──── kube-helm-chart
        │──── extensions-init-chart
        │──── cert-init-chart
        │──── base
        │──── meta
        │──── flow
        │      │──── ctp-chart
        │      │──── airflow-chart
        │            │──── airflow-postgres
        │──── monitoring
        │     │──── prometheus-chart
        │     │──── alertmanager-chart
        │     │──── grafana-chart
        │     │──── kube-state-metrics-chart
        │──── store
                │──── ohif-chart
                │──── minio-chart
                │──── minio-console-chart
                │──── minio-init-chart
                │──── dicom-init-chart
                │──── dcm4chee-chart
                    │──── dcm4che-ldap
                    │──── dcm4che-postgres
