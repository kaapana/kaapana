.. _faq_build_base_img:

How to build the base images
****************************

When base images like ``local-only/base-python-alpine:0.1.0`` are missing on your machine you could either build the whole platform (see :ref:`build`) or build only the required base images.
Building the whole platform is often not necessary and comes with some drawbacks (build time, space on your development machine) in case you only want to get your method in the platform by using the base images.

This guide assumes you have docker and git installed on your system (see :ref:`build` for details).

1. Clone the repository ``git clone -b master https://github.com/kaapana/kaapana.git``
2. Change working directory to the base image you want to build, e.g. ``cd kaapana/data-processing/base-images/base-python-alpine`` for the ``local-only/base-python-alpine:0.1.0`` image.
3. Build the image with docker ``docker build -t local-only/base-python-alpine:0.1.0 .``
