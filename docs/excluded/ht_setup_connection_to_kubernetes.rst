.. _setup_connection_to_kubernetes_doc:

Setup a connection to the Kubernetes cluster from your local workstation
========================================================================

Since the whole software runs within Kubernetes you can connect your local workstation directly to the server and are able to check if the containers
are running or not.

Installation of kubectl
^^^^^^^^^^^^^^^^^^^^^^^
Follow this instructions: `How to install Kubectl <https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl>`__

To enable the communication between kubectl and the Kubernetes API
server, you need to configure your kubectl with the Kubernetes certificate of the server.
To get this, you need to use the "jip_tools.sh" on the server with:

::

    ./jip_tools.sh --mode printconfig

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
    Di 5. Mär 18:08:15 CET 2019
