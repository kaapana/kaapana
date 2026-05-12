# Extension Manager Service

This is a FastAPI backend.

## Routers

The routers are separated into two modules

### Registry Manager

Contains endpoints and schemas to post new registries and get available registries.
Contains endpoints to retrieve a list of extensions and extensionManifests from a registry.

### Extension Manager

Contains endpoints and schemas to install and uninstall an extension.
Contains endpoints and schemas to get information about an installed extension and its content.


## Services

Communication to external services are separated into three modules

### OCI service

For communication with OCI registries.

### Dispatch service

For communication with consumers of extension content.

### Database service

Communication with the database.