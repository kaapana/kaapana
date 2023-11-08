package httpapi.authz

whitelisted_endpoints := [
    "^/auth/realms/kaapana/.*", 
    "^/auth/resources/.*"
    ]

allowed_user_endpoints := [
    "^/img/.*",
    "^/fonts/.*",
    "^/favicon.ico",
    "^/jsons/.*",
    "^/js/.*",
    "^/images/.*",
    "^/css/.*",
    "^/oauth2/.*",
    "^/web-ide",
    "^/pacs",
    "^/minio-console.*",
    "^/ohif.*",
    "^/kaapana-backend/.*",
    "^/dcm4chee-arc/.*",
    "^/meta/.*",
    "^/slim.*",
    "^/mitk-workbench-chart-.*",
    "^/slicer-workbench-chart-.*",
    "^/data-upload",
    "^/datasets",
    "^/workflow-execution",
    "^/workflows",
    "^/results-browser",
    "^/web/meta/.*",
    "^/web/store/.*",
]

allowed_admin_endpoints := [
    "^/.*"
    ]
