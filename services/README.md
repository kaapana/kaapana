# Modules
Contains all infrastructure building blocks of kaapana.

Each block should include:
1)  A Dockerfile and all necessary dependencies.
    If the component itself comes with its own repository, it should be cloned within the Docker build process.

2) A Helm chart, which defines the Kubernetes deployment for the platform.

