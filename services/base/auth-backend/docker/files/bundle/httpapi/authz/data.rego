package httpapi.authz

whitelisted := [
    "/oauth2/metrics", 
    "/auth/realms/kaapana", 
    "/auth/resources", 
    "/kaapana-backend/remote/",
    "/img/",
    "/fonts/",
    "/favicon.ico",
    "/jsons/",
    "/js/",
    "/images/"
    ]

user := [
"/meta", 
    "/dcm4chee-arc", 
    "/flow", 
    "/ohif", 
    "/web-ide", 
    "/minio-console", 
    "/jupyterlab", 
    "/qpsma", 
    "/doccano", 
    "/grafana", 
    "/prometheus",
    "/kaapana-backend/",
    "/kube-helm-api/",
    "/minio-console/",
    "/api/",
    "/oauth2/"
    ]

admin := [
    "/meta", 
    "/dcm4chee-arc", 
    "/flow", 
    "/ohif", 
    "/workflowdata", 
    "/web-ide", 
    "/minio-console", 
    "/jupyterlab", 
    "/qpsma", 
    "/doccano", 
    "/kubernetes", 
    "/traefik", 
    "/grafana", 
    "/prometheus",
    "/auth"
    ]
