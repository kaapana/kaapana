package httpapi.authz

import data.httpapi.authz.whitelisted_endpoints
import data.httpapi.authz.endpoints_per_role
import future.keywords.in

default allow := false

# Allow access to whitelisted endpoints
allow {
    some j
    regex.match(whitelisted_endpoints[j].path, input.requested_prefix)
}

allow {
    input.requested_prefix == "/"
}

### Allow access to endpoints depending on the realm-role
allow {
    some i 
    role := input.access_token.realm_access.roles[i]
    some j
    endpoint := endpoints_per_role[role][j]
    regex.match(endpoint.path, input.requested_prefix)
    some k
    endpoint.methods[k] == input.method
}

### Allow access to kaapana-backend if the user has the correct value in the kaapana_backend claim
allow {
    regex.match("^/kaapana-backend/.*", input.requested_prefix)
    
    some p
    kaapana_backend_claim := input.access_token.kaapana_backend[p]
    claim_matches := regex.find_all_string_submatch_n(`^all_(.+)$`, kaapana_backend_claim, -1)
    claim_project := claim_matches[0][1]

    claim_project == input.project.id
}

### Allow access to multiinstallable applications only in projects, where the user is part of.
allow {
    some p
    project := input.access_token.projects[p]
    project.role_name in ["admin","read"]
    project_application_regex := concat("/", ["^","applications","project",project.name,".*"])
    regex.match(project_application_regex, input.requested_prefix)
}

### Allow user with claim aii.manage_project_users_<project-id> to change the role of a user in the project with <project-id> 
allow {
    # Extract project-id from requested_prefix
    matches := regex.find_all_string_submatch_n(`^/aii/projects/([^/]+)/(?:role|user)/.*`, input.requested_prefix, -1)
    project_id := matches[0][1]

    # For each aii claim, check whether it matches manage_users_<project-id>
    some p
    claim_matches := regex.find_all_string_submatch_n(`^manage_users_(.+)$`, input.access_token.aii[p], -1)
    claim_project := claim_matches[0][1]

    project_id == claim_project
}

### Allow user with claim aii.manage_software_<project-id> to change the role of a user in the project with <project-id> 
allow {
    # Extract project-id from requested_prefix
    matches := regex.find_all_string_submatch_n(`^/aii/projects/([^/]+)/software-mappings/.*`, input.requested_prefix, -1)
    project_id := matches[0][1]

    # For each aii claim, check whether it matches manage_software_<project-id>
    some p
    claim_matches := regex.find_all_string_submatch_n(`^manage_software_(.+)$`, input.access_token.aii[p], -1)
    claim_project := claim_matches[0][1]

    project_id == claim_project
}