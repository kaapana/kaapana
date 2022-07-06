Proxy configuration
-------------------

If you need to configure a proxy in your institution to access internet, you can do this as following:

| Open **/etc/environment** with vi insert:

| http\_proxy="your.proxy.url:port"
| https\_proxy="your.proxy.url:port"

| HTTP\_PROXY="your.proxy.url:port"
| HTTPS\_PROXY="your.proxy.url:port"

::

    logout

Login again

::

    ping www.dkfz-heidelberg.de 

Should work -> network connection is working

.. _faq_doc kubernetes_connection:


Setup a connection to the Kubernetes cluster from your local workstation
------------------------------------------------------------------------

Since the whole software runs within Kubernetes you can connect your local workstation directly to the server and are able to check if the containers
are running or not.

Installation of kubectl
^^^^^^^^^^^^^^^^^^^^^^^
Follow this instructions: `How to install Kubectl <https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl>`__

To enable the communication between kubectl and the Kubernetes API
server, you need to configure your kubectl with the Kubernetes certificate of the server.
To get this, you need to use the "jip_tools.sh" on the server with:

::

    cat ~/.kube/config

To configure your local machine, you need to create a config file at:

::

    nano ~/.kube/config 

Paste the certificate from above in the file. You should now be able to
communicate with the Kubernetes instance. 

| To check the functionality, you can try:

::

    kubectl get pods --all-namespaces

You should now see a list of some Kubernetes resources.

**IF NOT:** Check the IP-address at the beginning of your config file.

::

    server: <SERVER-IP-ADDRESS>

This should match the IP you are using for SSH into the server.

**ELSE:** Check the date on the server!

Check if the datetime is correct by:

::

    date
    Di 5. Mär 18:08:15 CET 2020