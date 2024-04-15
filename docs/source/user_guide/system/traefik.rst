.. _traefik:

Traefik
^^^^^^^^^^

Traefik serves as the ingress controller for our system.
Every authenticated request originating from the client-side traverses through Traefik, which efficiently routes it to the appropriate service within the Kubernetes cluster.
Additionally, Traefik applies route-specific middlewares to enhance request handling.
Its user interface provides a comprehensive overview of all routers, services, and middlewares, allowing easy monitoring and management.
Furthermore, Traefik displays warnings or errors, in case of unintended behaviors.