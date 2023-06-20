System
------

This section provides a view of the technologies that run inside the Kaapana platform.
The core of the platform is a Kubernetes cluster, which is a container-orchestration system managing all the containers the platform consists of.
To manage the Kubernetes deployments a tool called Helm is used.
Ingress into the platform is managed by Traefik which serves as reverse proxy.
OAuth2-Proxy and Keycloak are used for access control and user management.
To provide a coherent interface the *landing page* wraps all of the services into one uniform web interface.


To find out more about the technologies checkout:

* `Helm <https://helm.sh/>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_
* `Grafana <https://grafana.com/>`_
* `Traefik <https://doc.traefik.io/traefik/>`_
* `Keycloak <https://www.keycloak.org/documentation.html>`_


Keycloak
^^^^^^^^

Keycloak is an open source identity and access management solution that we integrated in our platform to manage authentication and different user roles. 
It can be accessed via *System* menu in the web interface.

Currently there are two user roles: The **admin** has some more privileges than a normal **user**, i.e. a **user** can not access the Kubernetes dashboard and can not see all components on the landing page.

.. hint::
    Keycloak provides various options to integrate with your environment. Please check out the `documentation of Keycloak <https://www.keycloak.org/documentation.html>`_ for more details.

Here two examples how user management can be done with Keycloak:
* **Adding a user manually**: Once you are logged in you can add users in the section **Users**. By selecting a user you can change i.e. the password in the tab **Credentials** or change the role under **Role mappings**. Try i.e. to add a user who has no admin rights, only user rights. 
* **Connecting an Active Directory**: In order to connect to an active directory go to the tap **User Federation**. Depending on your needs select *ldap* or *kerberos*. The necessary configuration you should be able to get from your institution. If everything is configured correctly you are able to login with the credentials from the Active Directory.



Monitoring
^^^^^^^^^^

In order to monitor whats the current status of the Kaapana platform a monitoring stack consisting of `Prometheus <https://prometheus.io/>`_ and `Grafana <https://grafana.com/>`_. Prometheus stores various metrics in the form of time series which can be displayed via Grafana. Grafana can be accessed via the *System* menu. Here things like disk space, CPU and GPU memory usage or network pressure can be visually inspected.


Kubernetes
^^^^^^^^^^

As mentioned above, Kubernetes is at heart of the whole platform. You can interact with Kubernetes either via the Kubernetes Dashboard, accessible on the *System* menu in the web interface or directly via the terminal using `kubectl` on the server. In case anything on the platform is not working, Kubernetes is the first place to go.
To debug using Kubernetes, refer to :ref:`faq_debug_kubernetes`.



