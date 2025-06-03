.. _requirements:

Requirements
************

This document outlines the system requirements for operating a Kaapana instance.
Please note that if you intend to build or contribute to the development of Kaapana, different requirements may apply (especially on the networking side).

Hardware Requirements
=====================

.. list-table:: Hardware Requirements
   :header-rows: 1
   :widths: 30 40 30

   * - Component
     - Minimum
     - Recommended
   * - OS
     - Ubuntu 22.04/24.04,

       Ubuntu Server 22.04/24.04,

       or AlmaLinux 9.3
     - – Ubuntu Server 24.04
   * - CPU
     - 8 cores
     - 16 cores or more 
   * - RAM
     - 64GB
     - 128GB or more
   * - Storage Platform

       (fast-data-dir)
     - 100GB
     - More than 200GB
   * - Storage Images

       (slow-data-dir)
     - 100GB
     - Size based on your requirements


Network Requirements
====================

The following table provides an overview of the required network ports and services for an online deployment of the Kaapana platform.

.. list-table:: Network Ports and Services
   :header-rows: 1
   :widths: 20 10 6 10 40 10 25

   * - Name
     - Scope
     - Port
     - Protocol
     - Description
     - Direction
     - Partner
   * - Webinterface
     - Local
     - 80
     - http
     - Redirects to the secure web interface
     - Ingress
     - Local workstations
   * - Webinterface

       (Secure)
     - Local
     - 443
     - https
     - Web interface of the platform (interaction, file upload)
     - Ingress
     - Local workstations
   * - DICOM
     - Local
     - 11112
     - DICOM DIMSE
     - DICOM C-STORE SCP to send images to the platform
     - Ingress
     - Local workstation / local PACS
   * - OCI-Registry Auth
     - External
     - 443
     - https
     - Authentication to download OCI-Registry content
     - Egress
     - Depends on your registry
   * - OCI-Registry Content
     - External
     - 443
     - https
     - Download of the container and charts constituting the platform. (may differ from OCI-Registry Auth authentication service)
     - Egress
     - Depends on your registry
   * - Federation API
     - External
     - 443
     - https
     - Communication with other Kaapana-Platforms
     - Ingress
     - The federation APIs of other Kaapana Instances (only needed for federated setups).
   * - nnUnet Model Repository
     - External
     - 443
     - https
     - The repository containing pretrained nnUnet Models
     - Egress
     - zenodo.org

.. hint::
   **Traffic Scope:**

   - **Local:** Traffic confined within your internal network.
   - **External:** Traffic that traverses the internet.

.. attention::
   The ingress/egress rules listed above represent the minimum required for operating the platform.
   During installation, additional ingress may occur when accessing the configured Ubuntu APT mirror or the Snap Store.

.. hint::
    | The platform is based on microk8s which opens certain ports for multi-node setups as listed in `their documentation <https://microk8s.io/docs/services-and-ports>`_. Since the platform is single-node these ports can be blocked for external traffic by the systems firewall if needed.
