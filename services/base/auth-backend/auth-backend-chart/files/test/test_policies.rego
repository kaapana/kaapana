package authz_test

import data.httpapi.authz.allow

test_allow_root {
    allow with input as {"requested_prefix": "/"}
}

test_allow_whitelisted_auth {
    allow with input as {"requested_prefix": "/auth/realms/kaapana/"}
}

test_allow_whitelisted_auth_resources {
    allow with input as {"requested_prefix": "/auth/resources/"}
}

test_allow_whitelisted_oauth {
    allow with input as {"requested_prefix": "/oauth2/metrics"}
}

test_allow_whitelisted_remote_backend {
    allow with input as {"requested_prefix": "/kaapana-backend/remote/"}
}

test_allow_admin {
    allow with input as {"access_token": {"realm_access" : {"roles": ["admin"] } }, "requested_prefix": "/anyroute", "method": "POST"}
}

test_deny_kubernetes_for_user {
    not allow with input as {"access_token": {"realm_access" : {"roles": ["user"] } }, "requested_prefix": "/kubernetes", "method": "POST"}
}

test_allow_kaapana_backend_for_admin {
    allow with input as {"access_token": {"realm_access" : {"roles": ["admin"] } }, "requested_prefix": "/kaapana-backend/", "method": "POST"}
}

test_allow_kaapana_backend {
    allow with input as {
        "project": {"id": 1}, 
        "requested_prefix": "/kaapana-backend/", 
        "method": "POST",
        "access_token": {"projects" : [{"id" : 1, "role_name":"admin"}] } 
        }
}

test_deny_kaapana_backend_if_no_project_given {
    not allow with input as {
        "project": {}, 
        "requested_prefix": "/kaapana-backend/", 
        "method": "POST",
        "access_token": {"projects" : [{"id" : 1}] } 
    }
}

test_deny_kaapana_backend_if_project_role_too_low {
    not allow with input as {
        "project": {"id": 1}, 
        "requested_prefix": "/kaapana-backend/", 
        "method": "POST",
        "access_token": {"projects" : [{"id" : 1, "role_name":"guest"}] } 
    }
}