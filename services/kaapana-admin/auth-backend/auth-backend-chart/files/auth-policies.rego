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

### Allow access to kaapana-backend if the Project header matches with a project in the project claim of the access token
allow {
    regex.match("^/kaapana-backend/.*", input.requested_prefix)
    some p
    input.access_token.projects[p].id == input.project.id

    # allow kaapana backend routs if user has access to any project indifferent of roles
    # input.access_token.projects[p].role_name in ["admin","read"]
}

### Allow access to multiinstallable applications only in projects, where the user is part of.
allow {
    some p
    project := input.access_token.projects[p]
    project.role_name in ["admin","read"]
    project_application_regex := concat("/", ["^","applications","project",project.name,".*"])
    regex.match(project_application_regex, input.requested_prefix)
}