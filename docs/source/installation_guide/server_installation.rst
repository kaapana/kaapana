Server Installation
*******************

#. **Host system**

   | You will need some kind of :term:`server` to run the platform on.
   | Minimum specs:

   - OS: Ubuntu 20.04/22.04 or Ubuntu Server 20.04/22.04
   - CPU: 8 cores (recommended 16+)
   - RAM: 64GB+ (recommended 128GB+) 
   - Storage for application-data (fast-dir): 100GB (recommended >200GB) 
   - Storage for imaging-data (slow-dir): depends on your needs 


#. **Access to a container registry or a tarball with built  containers**

   Before proceeding with further installation steps, make sure you have access to a container registry or a tarball with built Kaapana containers, otherwise please visit :ref:`build`.

   .. hint::

      | **Accessing container Registry or Tarball with Pre-built  Containers**
      | If you are interested in exploring our platform, we encourage you to get in touch with us (:ref:`contact`). Should you choose to do so, we will gladly offer you two options for accessing it. You can either receive credentials for our container registry or receive a tarball that includes the necessary  containers. With these options, you can directly deploy the platform without the need to go through the building process.

   To provide the services in Kaapana, the corresponding containers are needed.
   These can be looked at as normal binaries of Kaapana and therefore only need to be built if you do not have access to already built containers via a container registry or a tarball.

   .. .. mermaid::

   ..    flowchart TB
   ..       a1(Do you want to use a remote container registry or a tarball for your Kaapana installation?)
   ..       a1-->|Yes| a2(Do you already have access to a registry or a tarball containing all needed containers?)
   ..       a1-->|No| b1
   ..       a2-->|Yes| c1
   ..       a2-->|No| b1
   ..       b1(Build Kaapana) --> c1
   ..       c1(Install Kaapana)


Server Config
=============

Proxy
^^^^^

If you need to configure a proxy in your institution to access the internet, you can do this as follows:

#. Open **/etc/environment** on your deployment server:

    :code:`nano /etc/environment`

#. Insert the proxy variables for the proxy in your institution

    :: 

        http_proxy="your.proxy.url:port"
        https_proxy="your.proxy.url:port"
        HTTP_PROXY="your.proxy.url:port"
        HTTPS_PROXY="your.proxy.url:port"


#. Logout :code:`logout` and login again


#. Your network connection is working if you can reach the dkfz website or any other website:

    :code:`curl www.dkfz-heidelberg.de`


.. SSL/TLS Certificates
.. --------------------

Custom DNS Server
^^^^^^^^^^^^^^^^^

    You can configure a custom DNS :code:`my.custom.dns` by executing:

    :code:`sed -i 's/DNS=""/DNS="my.custom.dns"/' ./kaapana/server-installation/server_installation.sh`
    
    If not set manually, the DNS will be configured according to system information.



Installation of Server Dependencies 
===================================

This part describes the preparation of the host system for Kaapana.
Besides a few required software packages, mainly Microk8s is installed, to setup Kubernetes. 

.. hint::

  | **GPU support (Nvidia GPUs)**
  | GPU support requires the installation of Nvidia drivers.
  | Please make sure the :code:`nvidia-smi` command is working as expected!

Before the example platform "Kaapana-platform" can be deployed, all dependencies must be installed on the server. 
To do this, you can use the :term:`server-installation-script`, located at :code:`kaapana/server-installation/server_installation.sh`, by following the steps listed below.

1. Copy the script to your target-system (server)
2. Make it executable:

   | :code:`chmod +x server_installation.sh`

3. Execute the script:

   | :code:`sudo ./server_installation.sh`

4. Reboot the system 

   | :code:`sudo reboot`

5. (optional) Enable GPU support for Microk8s 

   | :code:`sudo ./server_installation.sh -gpu`

.. hint::

  | **Server Dependency Uninstallation**
  | To uninstall the server-packages, you can use :code:`sudo ./server_installation.sh --uninstall`
