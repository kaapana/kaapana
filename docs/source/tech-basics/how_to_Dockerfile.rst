.. _how_to_dockerfile:

How to write a Dockerfile for Kaapana?
========================================

In order to get an overview how to generally design Dockerfiles take a look at the following basic tutorials:

*  https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
*  https://chrisedrego.medium.com/20-best-practise-in-2020-for-dockerfile-bb04104bffb6
*  ...

Base images
-----------
Common base images which are frequently used in Kaapana Dockerfiles are "ubuntu:20.04" or "python:3.9-alpine". The selection of your base image should be guided by the following points:

*  Select small-sized base images to reduce the size of the images which are built from the Dockerfile
    *  Minimal base images are often tagged with –slim
    *  e.g. alpine
*  Functionality of the Docker image you are building:
    *  Are python packages installed using pip? —> base image must be capable to execute installations properly (build wheels, ...)
*  Your preferences in terms of package managers (e.g. Ubuntu base images use „apt“, Alpine images use „apk“)

Labels
------
Docker images can be labeled in the Dockerfile to organize the created Docker images, to provide further (meta) information and to enable automation. The Docker instruction ``LABEL`` does not add a layer on the image such that you do not have put all ``LABEL`` instructions in one line, although this is still supported. Labels which are used to organize the Kaapana Docker images are the following:

*  ``REGISTRY``: defines the registry to which the Docker image is pushed
    *  ``REGISTRY`` is an optional label
*  ``IMAGE``: defines the utilization of this image
*  ``VERSION``: clearly specified version of the Docker image which is built from this Dockerfile
    *  spedified versions are valuable for debugging instead of always using ``<image>:latest``
*  ``CI_IGNORE``: indicator for the CI build system of Kaapana to build certain containers if label is set to true
*  ``PROJECT``: **TODO: ???**

Package managers: apt, apk
--------------------------
Based on the selection of the base image, you have to load packages with different package managers: ``apt`` package manager (ubuntu/debain based), ``apk`` package manager (alpine based). It is recommended to cover as many ``apt``/ ``apk`` package installations as possible in one ``RUN`` statement, since each ``RUN`` statement adds a layer to the image. It is always recommended to not install any packages which are not used by any executive part of the code. In order to preserve a good overview over the installed packages, it is recommended to sort them in an alphabetical order.
In the following, best practices are given for both package manager:

*  ``apt`` package manager:
    *  Always execute ``apt-get update`` and ``apt-get install`` in the same ``RUN`` statement: ``RUN apt-get update && apt-get install –y <package-name>``
    *  Further reduce the image size by removing the apt-cache: add ``&& rm -rf /var/lib/apt/lists/*`` at the end of the ``RUN apt-get`` statement
*  ``apk`` package manager:
    *  Remove apk-cache: ``&& rm -rf /var/cache/apk/*`` or add ``--no-cache`` flag

Installation of python packages: ``pip install``
------------------------------------------------
Python packages are installed using pip. Thereby the following best practices are recommended:

*  Outsource all requirements to an external ``requirements.txt`` file which is located in ``/files/requirements.txt``
*  In the ``requirements.txt`` file, specify each python package with a fixed version (which works) such that the applications does not crash if the latest version of a pip python package does not support something anymore
*  Before installing any python package:
    *  ``COPY`` requirements.txt into the container's directories
    *  update pip itself first by running ``pip install --upgrade pip``
*  Do not install python packages which are un-used in the executed code

Multi-stage setups
------------------
Use multi-stage Dockerfiles if e.g. a Dockerfile conatins the building as well as the deployment of an application in order to seperate these two processes from each other. Thereby, all build dependencies are left behind in first (build) stage and only the "things" which are really needed are kept for the second stage.
Both stages have to be clearly marked as „build-stage“ (1st stage) and „runtime“ (2nd stage).

General advices
---------------

*  Avoid too many layers and try to reduce number of image layers
    *  ``RUN``, ``COPY``, ``ADD`` statements add layers to the Docker image
*  Exclude files which are not necessary to build the image or add them to a .dockerignore file
*  Order image layers from less frequently changed to frequently changed
*  Do not install un-used packages (with ``apt`` or ``apk``) or un-used requirements (with ``pip``)
*  Limit the workload of one container to one process
*  Only ``COPY`` specific files instead of whole directories (to avoid copying unwanted/sensitive data)
*  Utilize ``WORKDIR`` to avoid specifying lengthy paths when ``COPY`` files, ...

Example of a Kaapana Dockerfile for a **workflow**:
---------------------------------------------------
Write the processing algorithm of your workflow in a python file: ``example-workflow.py``.
Write the Dockerfile for the workflow which installs requirements, copies the ``example-workflow.py`` file and executes the algorithm.

.. code-block::

    FROM python:3.9-alpine3.12                              # small-sized alpine base image

    LABEL IMAGE="example-dockerfile-workflow"               # define utilization of image
    LABEL VERSION="0.1.0"                                   # define specific version of image
    LABEL CI_IGNORE="True"
    
    COPY files/requirements.txt /src/                       # copy outsourced requirements

    RUN pip3 install —upgrade pip                           # first upgrade pip
        && pip3 install -r /src/requirements.txt            # install outsourced requirements

    COPY files/example-workflow.py /                        # copy to-be-executed script

    CMD ["python3","-u","/example-workflow.py"]             # execute script

**TODO:**
* Dockerfile for service
* Dockerfile for extension