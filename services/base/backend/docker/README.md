# Kaapana Backend

## Building

### Container

The build context must be in the base directory because the backend needs to build the datamodel package's (pip) dependency.

Then you can build the backend using: `docker build -t registry.hzdr.de/$KAAPANA_REGISTRY_USERNAME/kaapana/backend:0.0.1 -f backend/docker/Dockerfile .` and `docker push $KAAPANA_REGISTRY/$KAAPANA_REGISTRY_USERNAME/kaapana/backend:0.0.1`

### Chart

0. `export HELM_EXPERIMENTAL_OCI=1` to support oci containers
1. `helm chart save backend-chart/ $KAAPANA_REGISTRY/$KAAPANA_REGISTRY_USERNAME/kaapana/backend-chart:0.0.1`
