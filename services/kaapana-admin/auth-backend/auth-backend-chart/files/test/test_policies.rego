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

test_allow_project_management {
    allow with input as {"access_token": {"realm_access" : {"roles": ["project-manager"] } }, "requested_prefix": "/aii/projects", "method": "POST"}
}

test_deny_project_management {
    not allow with input as {"access_token": {"realm_access" : {"roles": ["user"] } }, "requested_prefix": "/aii/projects", "method": "POST"}
}

test_deny_kubernetes_for_user {
    not allow with input as {"access_token": {"realm_access" : {"roles": ["user"] } }, "requested_prefix": "/kubernetes", "method": "POST"}
}

test_allow_kaapana_backend_for_admin {
    allow with input as {"access_token": {"realm_access" : {"roles": ["admin"] } }, "requested_prefix": "/kaapana-backend/", "method": "POST"}
}

test_allow_kaapana_backend {
    allow with input as {
        "project": {"id": "jkl-234-asd-234"}, 
        "requested_prefix": "/kaapana-backend/", 
        "method": "POST",
        "access_token": {"kaapana.ai/backend" : ["all_jkl-234-asd-234"] } 
        }
}

test_deny_kaapana_backend_if_no_correct_claim {
    not allow with input as {
        "project": {"id": "jkl-234-asd-234"}, 
        "requested_prefix": "/kaapana-backend/", 
        "method": "POST",
        "access_token": {"kaapana.ai/backend" : ["all_234-454-123-asd"] }
    }
}

test_deny_kaapana_backend_if_no_project_in_input {
    not allow with input as {
        "requested_prefix": "/kaapana-backend/", 
        "method": "POST",
        "access_token": {"projects" : [{"id" : 1}] } 
    }
}

test_allow_project_application {
    allow with input as {
        "requested_prefix": "/applications/project/234-asd-234-dfg-23r/release/jupyterlab-chart",
        "access_token": {"kaapana.ai/applications": ["open_234-asd-234-dfg-23r"]} 
    }
}

test_deny_project_application_because_project_does_not_match {
    not allow with input as {
        "requested_prefix": "/applications/project/234-asd-234-dfg-23r/release/jupyterlab-chart",
        "access_token": {"kaapana.ai/applications": ["open_123-234-345-456"]}
    }
}

test_allow_view_applications {
    allow with input as {
        "requested_prefix": "/kube-helm-api/extensions",
        "method": "GET",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["view_234-asd-234-dfg-23r"]}
    }
}

test_deny_view_applications_because_project_does_not_match {
    not allow with input as {
        "requested_prefix": "/kube-helm-api/extensions",
        "method": "GET",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["view_123-234-345-456"]}
    }
}

test_deny_view_applications_for_wrong_method {
    not allow with input as {
        "requested_prefix": "/kube-helm-api/extensions",
        "method": "POST",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["view_234-asd-234-dfg-23r"]}
    }
}

test_allow_launch_application {
    allow with input as {
        "requested_prefix": "/kube-helm-api/helm-install-chart",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["launch_234-asd-234-dfg-23r"]}
    }
}

test_deny_launch_application_because_project_does_not_match {
    not allow with input as {
        "requested_prefix": "/kube-helm-api/helm-install-chart",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["launch_123-234-345-456"]}
    }
}

test_allow_delete_active_apps {
    allow with input as {
        "requested_prefix": "/kube-helm-api/helm-delete-chart",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["delete_234-asd-234-dfg-23r"]}
    }
}

test_deny_delete_active_apps_because_project_does_not_match {
    not allow with input as {
        "requested_prefix": "/kube-helm-api/helm-delete-chart",
        "project": {"id": "234-asd-234-dfg-23r"},
        "access_token": {"kaapana.ai/applications": ["delete_123-234-345-456"]}
    }
}

test_allow_adding_user {
    allow with input as {
        "requested_prefix": "/aii/projects/123-234-123-345/user/",
        "access_token": {"kaapana.ai/aii" : ["manage_users_123-234-123-345"] } 
    }
}


test_deny_adding_user {
    not allow with input as {
        "requested_prefix": "/aii/projects/123-234-123-345/role/",
        "access_token": {"kaapana.ai/aii" : ["manage_users_123-234-123-asd"] } 
    }
}

test_allow_managing_software {
    allow with input as {
        "requested_prefix": "/aii/projects/123-234-123-345/software-mappings",
        "access_token": {"kaapana.ai/workflows" : ["manage_123-234-123-345"] }
    }
    allow with input as {
        "requested_prefix": "/flow/kaapana/api/getdags",
        "access_token": {"kaapana.ai/workflows" : ["manage_123-234-123-345"] }
    }
}


test_deny_managing_software {
    not allow with input as {
        "requested_prefix": "/aii/projects/123-234-123-345/software-mappings",
        "access_token": {"kaapana.ai/workflows" : ["manage_users_123-234-123-345"] }
    }
}