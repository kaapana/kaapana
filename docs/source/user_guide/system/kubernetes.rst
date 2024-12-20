.. _kubernetes:

Kubernetes
^^^^^^^^^^

Kubernetes is the core of the whole platform.
You can interact with Kubernetes either via the Kubernetes Dashboard, accessible on the *System* menu in the web interface or directly via the terminal using `kubectl` on the server. 
In case anything on the platform is not working, Kubernetes is the first place to go.
To debug using Kubernetes, refer to :ref:`faq_debug_kubernetes`.


Dashboard user permissions
****************************
We've implemented a new ClusterRole, `kaapana-kube-dashboard-production`, specifically tailored for the Kubernetes Dashboard. 
When the platform is deployed in production mode (i.e., :code:`DEV_MODE=false`), the ServiceAccount for the Kubernetes Dashboard is associated with this role. 
This ClusterRole grants restricted access to the Kubernetes API, enabling essential actions such as viewing, watching, listing, and deleting pods, as well as managing secrets. 
For ressources apart from pods and secrets only fundamental operations like viewing and listing are permitted. 
This enhancement serves to improve security measures for production environments.

In non-production systems the Kubernetes Dasboard can be used for unrestricted operations on Kubernetes resources.

.. _network_policies:

Network policies
*****************
To ensure a more encapsulated setup, all pods initiated by user actions operate within the `jobs` namespace of Kubernetes. 
We've implemented network policies to confine communication between pods within this namespace, restricting access to other containers in the platform. 
By default, these network policies prevent pods in this namespace from communicating with any other pod. 
For pods requiring external communication, we've introduced the :code:`network-access` label, offering options such as :code:`external-ips`, :code:`ctp`, and :code:`opensearch`.