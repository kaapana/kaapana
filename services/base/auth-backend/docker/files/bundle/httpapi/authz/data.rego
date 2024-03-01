package httpapi.authz

whitelisted_endpoints := [
    {"path": "^/auth/realms/kaapana/.*", "methods": ["GET","POST","PUT","DELETE"]}, 
    {"path": "^/auth/resources/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/oauth2/metrics", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kaapana-backend/remote/.*", "methods": ["GET","POST","PUT","DELETE"]},
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
    {"path": "^/pacs", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/minio-console.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/ohif.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kaapana-backend/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/dcm4chee-arc/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/meta/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/slim.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/mitk-workbench-chart-.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/slicer-workbench-chart-.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/data-upload", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/datasets", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/workflow-execution", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/workflows", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/results-browser", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/pending-applications", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/meta/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/web/store/.*", "methods": ["GET","POST","PUT","DELETE"]},
    {"path": "^/kube-helm-api/pending-applications", "methods": ["GET"]},
    {"path": "^/thumbnails/.*", "methods": ["GET"]}
]

allowed_admin_endpoints := [
    {"path":"^/.*", "methods": ["GET","POST","PUT","DELETE"]},
    ]

allowed_dcm4chee_admin_endpoints :=[
     {"path": "^/dcm4chee-arc/.*", "methods": ["GET","POST","PUT","DELETE"]},
]

endpoints_per_role := {
    "user" : allowed_user_endpoints,
    "admin" : allowed_admin_endpoints,
    "dcm4chee-admin": allowed_dcm4chee_admin_endpoints,
}
