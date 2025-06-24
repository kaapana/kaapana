.. _kubernetes:

Kubernetes
^^^^^^^^^^

:term:`Kubernetes<kubernetes>` is the core of the whole platform.
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

Network Policies
****************

This section has been moved to :ref:`Networking <network_policies>`