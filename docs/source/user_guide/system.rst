System
------

This section contains interfaces for the technologies that build the backbone of the Kaapana platform.
Access to this section is restricted to users with the `admin` role.
In Kaapana all applications, services and processes are containerized.
These containers are orchestrated and managed by a `Kubernetes <https://kubernetes.io/docs/concepts/>`_ cluster.
`Helm <https://helm.sh/>`_ is used to package and manage all Kubernetes resources.
For handling ingress into the platform, we rely on `Traefik <https://doc.traefik.io/traefik/>`_, which serves as our reverse proxy. 
Access control and user management are managed through OAuth2-Proxy and `Keycloak <https://www.keycloak.org/documentation.html>`_.
To monitor the platform's health and status, we offer `Prometheus <https://prometheus.io/>`_ and `Grafana <https://grafana.com/>`_. 
These tools provide comprehensive insights into various metrics and performance indicators.
All data-processing in the platform is based on Directed-Acyclic-Graphs (DAGs) defined in `Airflow <https://airflow.apache.org/docs/apache-airflow/stable/index.html>`_


.. toctree::
    :maxdepth: 2

    system/airflow
    system/kubernetes
    system/keycloak
    system/traefik
    system/monitoring