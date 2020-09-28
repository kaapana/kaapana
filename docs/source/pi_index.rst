.. _pi_index_doc:

.. Kaapana documentation master file, created by
   sphinx-quickstart on Fri Oct 19 11:13:54 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Platform Installation
*********************

| To perform the installation, the network configuration of the server must be known.

This consists of the following parts:

    - IP address
    - Domain and hostname
    - Netmask
    - Gateway
    - DNS servers
    - Search domains
    - Proxy configuration (if needed)

**The server needs internet access during the installation!**

| The installation of Kaapana will be done in **three steps**:

1. A plain Minimal CentOS 7 will be installed on the server (:ref:`centos_install_doc`).
2. All required dependencies will be installed on the plain CentOS (:ref:`kaapana_dependencies_doc`).
3. The platform itself will be deployed (:ref:`platform_deployment_doc`).

| Please follow the steps mentioned. If you have issues feel free to contact us: jip-service@dkfz-heidelberg.de

.. note::

  | For technical issues and questions related to the server, you can contact the responsible company directly:
  | ProCom 
  | Kundenservice: 07161-93200-0 



.. raw:: latex

    \clearpage


.. toctree::
   :maxdepth: 2

   pi_1_centos_installation
   pi_2_kaapana_dependencies
   pi_3_platform_deployment




