# Extension Manager Service

This is a FastAPI backend.

## Routers

The routers are separated into two modules

### Repository

Contains endpoints and schemas to post new repositories and get available repositories.
Contains endpoints to retrieve a list of extensions and extensionManifests from a registry.

### Installation

Contains endpoints and schemas to install and uninstall an extension.
Contains endpoints and schemas to get information about an installed extension and its content.


## Services

Communication to external services are separated into three modules

### OCI service

For communication with OCI repositories.

### Dispatch service

For communication with consumers of extension content.

### Database service

Communication with the database.