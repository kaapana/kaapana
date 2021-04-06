.. _getting_started:

Getting started
===============

This manual is intended to provide a quick and easy way to get started with :ref:`Kaapana<what_is_kaapana>`.
Kaapana is not a ready-to-use software but a toolkit that enables you to build the platform that fits your specific needs.
The steps described in this guide will build an example :term:`platform`, which is a default configuration and contains many of the typical platforms :term:`components<component>`. 
This basic platform can be used as a starting-point to derive a customized platform for your specific project.

Whats needed to run Kaapana?
----------------------------

#. Registry

.. mermaid::

   graph TD
      A([Do you have access to an existing container registry?]) -->|Yes| B([Does this registry already contain the Kaapana containers?])
      B -->|Yes| C([You can skip the Kaapana build and continue with the Kaapana installation]);
      B -->|No| D([You need to Build Kaapana]);
      C --> E([Continue with Kaapana installation]);
      A -->|No| D([You need to Build Kaapana]);

.. mermaid::

   graph TB
      subgraph registry
      a1(Do you want to use a remote container registry?)
      a1-->|No| a2(Use build-mode: 'local')
      a1-->|Yes| a3(Do you have acces to an existing registry?)
      a3-->|Yes| a4(Does it contain all Kaapana containers already?)
      end
      subgraph build
      end
      subgraph installation
      end
      a1(Do you have acces to an existing registry containing Kaapana containers?)-->|No| b1
      a1-->|Yes| c1
      b1(Build Kaapana)
      b1-->|local build| b2 
      b1-->|registry| b3
      end
      subgraph install
      c1(prepare host-system)-->c2(deploy Kaapana)
      end

To provide the services in Kaapana, the corresponding containers are needed.
These can be looked at as normal binaries of Kaapana and therefore only need to be built if you do not have access to already built containers via a Docker Registry. 

#. Target-system

| You will need some kind of :term:`server` to run the platform on.
| Minimum specs:

- OS: CentOS 8, Ubuntu 20.04 or Ubuntu Server 20.04
- CPU: 4 cores 
- Memory: 8GB (for processing > 30GB recommended) 
- Storage: 100GB (deploy only) / 150GB (local build)  -> (recommended >200GB) 

| The **domain,hostname or IP-address** has to be known and correctly configured for the system. 
| If a **proxy** is needed, it should already be configured at ``/etc/environment`` (reboot needed after configuration!). 


**Filesystem directories:** In the default configuration there are two locations on the filesystem. Per default, the two locations are the same, if you have a SSD and a HDD mount, you should adapt the directory, which are defined in the :term:`platform-installation-script` accordingly, before executing the script.

1. ``fast_data_dir=/home/kaapana``: Location of data that do not take a lot of space and should be loaded fast. Preferably, a SSD is mounted here.

2. ``slow_data_dir=/home/kaapana``:  Location of huge files, like images or our object store is located here.  Preferably, a HDD is mounted here.

**Supported browsers:** As browsers to access the installed platform we support the newest versions of Google Chrome and Firefox. With Safari it is currently not possible to access Traefik as well as services that are no vnc desktops. Moreover, Some functionalities in OHIF viewer do not work with Safari. Internet Explorer and Microsoft Edge are not really tested. 


#. Installation

