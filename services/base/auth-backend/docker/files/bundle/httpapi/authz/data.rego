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
    "^/oauth2/.*",
    "^/web-ide",
    "^/minio-console.*",
    "^/ohif/.*",
    "^/kaapana-backend/.*",
    "^/dcm4chee-arc/.*",
    "^/meta/.*",
    "^/slim.*",
    "^/mitk-workbench-chart-.*",
    "^/slicer-workbench-chart-*"
]

allowed_admin_endpoints := [
    "^/.*"
    ]
