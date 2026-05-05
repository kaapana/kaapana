# Extension Manager Service

This is a FastAPI backend.

## Routers

The routers are separated into three modules

### Registry Manager

Contains endpoints and schemas to post new registries and get available registries.

### Installation Manager

Contains endpoints and schemas to install and uninstall an extension.

### Extension State Manager

Contains endpoints and schemas to get information about the state of an installed extension.


## Services

Communication to external services are separated into three modules

### OCI service

For communication with OCI registries.

### Consumer service

For communication with consumers of extension content.

### Database service

Communication with the database.