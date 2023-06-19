Introduction
************

This manual serves as a resource for getting started with :ref:`Kaapana<about_kaapana>`. Kaapana is a highly customizable platform toolkit designed to facilitate the creation of a platform tailored to the specific requirements of your project. 
It provides a core system along with several pre-built functionalities, such as image curation, workflow management, and training and inference capabilities for medical imaging models (specifically nnUnet). 

If you want to deploy the platform as it is, you can request access to our container registry through `Slack <https://kaapana.slack.com/archives/C018MPL9404>`_. While the platform can be adjusted manually with additional extensions, custom web applications, and manually defined workflows, 
for more extensive development, we recommend following the :ref:`build process<build>` to populate a custom registry with your own images.

Refer to the flowchart below for deciding which section of the installation guide is relevant for your use case.

.. mermaid::

    flowchart TB
        a1(Do you want to use a remote container registry or a tarball for your Kaapana deployment?)
        a1-->|Yes| a2(Do you already have access to a registry or a tarball containing all containers?)
        a1-->|No| b1
        a2-->|Yes| c1
        a2-->|No| b1
        b1(Build Kaapana) --> c1
        c1(Platform Deployment)