package httpapi.authz

import data.httpapi.authz.whitelisted_endpoints
import data.httpapi.authz.endpoints_per_role

# Allow access to whitelisted endpoints
allow {
    some j
    regex.match(whitelisted_endpoints[j].path, input.requested_prefix)
}

allow {
    input.requested_prefix == "/"
}

### Allow access to endpoints depending on the role
allow {
    some i 
    role := input.access_token.realm_access.roles[i]
    some j
    endpoint := endpoints_per_role[role][j]
    regex.match(endpoint.path, input.requested_prefix)
    some k
    endpoint.methods[k] == input.method
}

### Allow access to application entities in dcm4chee based on user attribute application_entity
allow {
    regex.match("^/dcm4chee-arc/aets/.*", input.requested_prefix)
    some i
    checking_regex := concat("",["^/dcm4chee-arc/aets/", input.access_token.application_entity[i], "/.*"])
    regex.match(checking_regex, input.requested_prefix)
}