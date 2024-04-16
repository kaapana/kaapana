.. _how_to_dockerfile:

Writing Dockerfile
**********************************

.. important:: 
    | In order to get an overview how to generally design Dockerfiles take a look at the following basic tutorials:
    | - Docker_
    | - Medium_

Base images
-----------
Kaapana Dockerfiles typically utilize base images such as :code:`ubuntu:20.04` or :code:`python:3.9.16-slim`. However, it's strongly advised to use the pre-existing base images located under :code:`data-processing/base-images` in the Kaapana project. For tasks requiring Python, consider using the :code:`base-python-cpu` or :code:`base-python-gpu` images for CPU-bound and GPU-accelerated tasks, respectively.

When selecting your own base image, you should consider:

- **Size**: Smaller base images can help reduce the total size of the Docker images that you build. Therefore, minimal base images that are tagged with :code:`:slim` (such as :code:`alpine:slim`) are generally a good choice.
- **Functionality**: If your Docker image requires Python packages installed via :code:`pip`, ensure your base image can correctly handle such installations, including the building of wheels.
- **Package Manager Preference**: Different base images come with different package managers. For instance, Ubuntu base images use :code:`apt`, while Alpine images use :code:`apk`.

Labels
------

Labels in Dockerfiles serve multiple purposes. They help to categorize Docker images, provide additional metadata, and facilitate automation. The `LABEL` Docker instruction does not introduce a new layer in the image, therefore, you can freely include multiple `LABEL` instructions in the Dockerfile, without worrying about increasing the number of layers.

Kaapana Docker images often utilize the following labels:

- `REGISTRY`: Specifies the target registry for pushing the Docker image. This is an optional label, and can be used to control where the built image is stored.
- `IMAGE`: Defines the intended usage of the image. It can be used to quickly identify the purpose of a particular image.
- `VERSION`: Indicates the version of the Docker image that is built from the Dockerfile. Providing explicit versions helps with traceability and debugging, instead of just using the :code:`<image>:latest` tag.
- `BUILD_IGNORE`: A flag used by the Kaapana build system. If this label is set to true, it will prevent specific containers from being built.

Package managers: apt, apk
--------------------------
Depending on the base image chosen, different package managers will be utilized: :code:`apt` for Ubuntu/Debian-based images, and :code:`apk` for Alpine-based images. To optimize your Dockerfile, aim to install as many packages as possible within a single :code:`RUN` statement. This is due to the fact that each :code:`RUN` statement introduces a new layer to the Docker image.

Ensure you only install packages that are necessary for the execution of your code. Maintaining an alphabetically sorted list of installed packages can help keep track of them.

Below are best practices for using the :code:`apt` and :code:`apk` package managers:

- :code:`apt` package manager:
  - Always combine :code:`apt-get update` and :code:`apt-get install` within the same :code:`RUN` statement: :code:`RUN apt-get update && apt-get install -y <package-name>`
  - To further minimize the image size, remove the apt-cache by appending :code:`&& rm -rf /var/lib/apt/lists/*` to the end of the :code:`RUN apt-get` statement.

- :code:`apk` package manager:
  - Clear the apk-cache by appending :code:`&& rm -rf /var/cache/apk/*` to your :code:`apk add` command, or use the :code:`--no-cache` flag when installing packages to avoid creating the cache in the first place.

Installation of python packages: ``pip install``
------------------------------------------------
Python packages are usually installed using pip, Python's package installer. The following practices are recommended for effectively managing package installations:

- **Use a requirements file**: Move all package dependencies to an external :code:`requirements.txt` file, typically located at :code:`/files/requirements.txt`. This helps to keep the Dockerfile clean and improves readability.

- **Pin package versions**: In the :code:`requirements.txt` file, specify a fixed version for each Python package. This ensures that your application does not break if a newer version of a package is released that changes or removes functionality your application relies on.

- **Prepare for installation**: Before installing any Python package, perform the following steps:
  - Copy the :code:`requirements.txt` file into the container's directory structure using the :code:`COPY` command.
  - Update pip itself first by running :code:`pip install --upgrade pip`. This ensures you're using the latest version of pip, which can help avoid installation issues.

- **Avoid installing unused packages**: Do not install Python packages that are not used by the executed code. This reduces the image size and avoids potential security vulnerabilities.

When installing Python packages, it's also recommended to use a constraints file. This helps ensure compatibility and stability across different environments. For example, Kaapana provides a constraints file that can be used with the :code:`pip install` command:

.. code-block:: bash

  pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt <package-name>


Utilizing Multi-Stage Dockerfiles
---------------------------------
Multi-stage Dockerfiles are particularly useful when a Dockerfile contains both the building and the deployment of an application. They allow these two processes to be separated from each other. All build dependencies are left behind in the first (build) stage, while only the essential "artifacts" are preserved for the second stage. Both stages should be clearly marked as "build-stage" (1st stage) and "runtime" (2nd stage).

General Guidelines
------------------

Here are some additional Docker best practices to adhere to:

- **Minimize Layer Count**: Avoid creating too many layers and strive to reduce the number of image layers. Instructions such as :code:`RUN`, :code:`COPY`, and :code:`ADD` add layers to the Docker image.

- **Exclude Unnecessary Files**: Exclude files that are not necessary for building the image or add them to a :code:`.dockerignore` file. This helps to keep the image size minimal and prevents the inclusion of unwanted or sensitive data.

- **Order Image Layers**: Arrange image layers from the least frequently changed to the most frequently changed. This allows Docker to cache layers, improving the speed of image building and pulling.

- **Avoid Installing Unused Packages**: Do not install packages that are not used, whether using :code:`apt` or :code:`apk` for system packages, or :code:`pip` for Python packages.

- **Limit Workload of Containers**: Limit the workload of a single container to one process. This follows the principle of single responsibility and makes container management easier.

- **Copy Specific Files**: Only copy specific files instead of whole directories, again, to avoid including unwanted or sensitive data.

- **Utilize WORKDIR**: Use the :code:`WORKDIR` instruction to avoid specifying lengthy paths when using :code:`COPY` and other instructions. This makes Dockerfiles more readable and easier to maintain.


Example of a Kaapana Dockerfile for a workflow
-----------------------------------------------

Assume that the processing algorithm of your workflow is written in a Python file named :code:`example-workflow.py`. The Dockerfile for the workflow should install the necessary requirements, copy the :code:`example-workflow.py` file into the Docker image, and define a command to execute the algorithm. Here is an example Dockerfile:

.. code-block::

  # Dockerfile
  # Base Image - Using a slim and small-sized Python base image
  FROM python:3.9.16-slim

  # LABELS - To organize Kaapana Docker images
  LABEL REGISTRY="example-registry"
  LABEL IMAGE="example-dockerfile-workflow"
  LABEL VERSION="0.1.0"
  LABEL BUILD_IGNORE="False"

  # Setting up the working directory
  WORKDIR /app

  # Update pip first and install the necessary Python packages using constraints file
  COPY files/requirements.txt .
  RUN pip install --upgrade pip && \
      pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r requirements.txt

  # Copy only the necessary script to be executed
  COPY files/example-workflow.py .

  # Define the command to execute the script
  CMD ["python3","-u","example-workflow.py"]

.. _Docker: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
.. _Medium: https://chrisedrego.medium.com/20-best-practise-in-2020-for-dockerfile-bb04104bffb6

=======

To build and push the docker container, run the following commands:

.. code-block:: bash

  docker build -t <docker-registry><docker-repo>/example-extract-study-id:0.1.0 .
  docker push <docker-registry><docker-repo>/example-extract-study-id:0.1.0
