.. _platform_deployment_doc:

Platform Deployment
===================

This part is about the deployment of the platform components themselves.
You can do this directly on the server or remote from your machine via ssh. 

Requirements
------------

The following requirements should be met:

- CentOS installed  (:ref:`centos_install_doc`)
- All dependencies are installed (:ref:`kaapana_dependencies_doc`)
- System reboot
- Kubernetes up and running -> you can check this on the server:

::

    kubectl get pods --all-namespaces

In order to keep your system clean before installing the new version you can delete all unused and just dangling docker images. However, this step is optional.

::

    docker system prune -a


.. _installation deployment:


Deployment of Kaapana
----------------------------------------
First you need to download the installer script for the jip-platform.

::

    curl -L -O https://jip.dktk.dkfz.de/42fef1/jip_installer.sh

You should now find the script in your current path.


Make the script executable with:

::

    chmod +x jip_installer.sh

Start the deployment
--------------------
::

    ./jip_installer.sh --mode install-chart

After the deployments were sent to the server, you have to wait for the
platform to come alive. This could take some time, because all the
components have to be downloaded to the server. 

.. raw:: latex

    \clearpage

| You can check the process by using:

::

    watch kubectl get pods --all-namespaces

You will get a list of all components and the state they are currently in.

::

                 READY                          STATUS
        num_running/num_expected      Should be Running or completed

.. hint::
    
    Initialization takes some time - give the system around 30 min and check again.*

You should wait till all components are either in the running or completed state.

If you see and error or container restart listed, it is not necessarily a reason to worry.

The system tries to bring itself in the right condition.

If you still have some issues with this process you should contact the Kaapana team (See :ref:`license_doc`).

Now you can visit your server at:

::

    https://<server-domain>/

And should be welcomed by a login-screen.

**DEFAULT CREDENTIALS**

| username: kaapana
| password: kaapana


You will be asked to change the password.

**OPTIONAL:**

For development purposes and convenience reasons it is possible to connect directly to the Kubernetes cluster from your local workstation.
The setup steps can be found on the page :ref:`setup_connection_to_kubernetes_doc` .

.. raw:: latex

    \clearpage