.. _getting_started:

Getting started
===============

This manual is intended to provide a quick and easy way to get started with :ref:`Kaapana<what_is_kaapana>`.
Kaapana is not a ready-to-use software but a toolkit that enables you to build the platform that fits your specific needs.
The steps described in this guide will build an example :term:`platform`, which is a default configuration and contains many of the typical platforms :term:`components<component>`. 
This basic platform can be used as a starting-point to derive a customized platform for your specific project.

What's needed to run Kaapana?
-----------------------------

#. **Host System**

   | You will need some kind of :term:`server` to run the platform on.
   | Minimum specs:

   - OS: CentOS 8, Ubuntu 20.04 or Ubuntu Server 20.04
   - CPU: 4 cores 
   - Memory: 8GB (for processing > 30GB recommended) 
   - Storage: 100GB (deploy only) / 150GB (local build)  -> (recommended >200GB) 

#. **Container Registry**

   .. hint::

      | **Get access to our docker registry**
      | In case you just want to try out the platform, you are very welcome to reach out to us via slack_ or email_. In this case, we will provide you credentials to our docker registry from which you can directly install the platform and skip the building part!

   To provide the services in Kaapana, the corresponding containers are needed.
   These can be looked at as normal binaries of Kaapana and therefore only need to be built if you do not have access to already built containers via a container registry.
   This flow-chart should help you to decide if you need to build Kaapana and which mode to choose:

   .. mermaid::

      flowchart TB
         a1(Do you want to use a remote container registry for your Kaapana installation?)
         a1-->|Yes| a2(Do you already have access to a registry containing all needed containers?)
         a1-->|No| b1
         a2-->|Yes| c1
         a2-->|No| b1
         b1(Build Kaapana) --> c1
         c1(Install Kaapana)

#. **Build**

   :ref:`build_kaapana`

#. **Installation**

   :ref:`install_kaapana`


   .. _email: mailto:kaapana@dkfz-heidelberg.de?subject=kaapana%20Support%20Question
   .. _slack: https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ/
