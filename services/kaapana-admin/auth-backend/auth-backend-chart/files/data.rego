package httpapi.authz

whitelisted_endpoints := [
    {"path": "^/auth/realms/kaapana/.*", "methods": ["GET","POST","PUT","DELETE"]}, 
    {"path": "^/auth/resources/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/oauth2/metrics", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kaapana-backend/remote/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kaapana-backend/oidc-logout", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/docs/", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/system/Documentation", "methods": ["GET","POST","PUT","DELETE"]},
]

allowed_user_endpoints := [
    {"path": "^/img/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/fonts/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/favicon.ico", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/jsons/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/js/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/images/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/css/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/oauth2/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web-ide", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/minio-console.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/ohif.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/dicom-web-filter/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/meta/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/slim.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/mitk-workbench-chart-.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/slicer-workbench-chart-.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/data-upload", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/datasets", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/workflow-execution", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/workflows", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/results-browser", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/active-applications", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kube-helm-api/complete-active-application", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/meta/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/store/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/system/Projects.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kube-helm-api/active-applications", "methods": ["GET"]},
    {"path": "^/thumbnails/.*", "methods": ["GET"]},
    {"path": "^/aii/.*", "methods": ["GET"]},
    {"path": "^/projects-ui.*", "methods": ["GET"]},
    {"path": "^/kaapana-backend/client/file", "methods": ["POST", "HEAD", "PATCH","DELETE"]},
    {"path": "^/collabora-wopi/", "methods": ["GET"]},
    {"path": "^/collabora-wopi/documents.*", "methods": ["GET","PUT" ,"POST", "HEAD", "PATCH","DELETE"]},
    {"path": "^/collabora/.*", "methods": ["GET","PUT" ,"POST", "HEAD", "PATCH","DELETE"]},
    {"path": "^/notifications/.*", "methods": ["GET", "POST", "PUT"]},
]

allowed_project_manager_endpoints := [
    {"path": "^/aii/.*" ,"methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/system/Projects.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/projects-ui.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kaapana-backend/open-policy-data", "methods": ["GET"]},
    {"path": "^/kaapana-backend/settings", "methods": ["GET"]},
    {"path": "^/kaapana-backend/get-traefik-routes", "methods": ["GET"]},
]

allowed_admin_endpoints := [
    {"path":"^/.*", "methods": ["GET","POST","PUT","DELETE","HEAD","PATCH"]},
]

endpoints_per_role := {
    "user" : allowed_user_endpoints,
    "admin" : allowed_admin_endpoints,
    "project-manager": allowed_project_manager_endpoints
}