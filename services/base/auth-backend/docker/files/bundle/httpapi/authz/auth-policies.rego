package httpapi.authz

import data.httpapi.authz.allowed_admin_endpoints
import data.httpapi.authz.allowed_user_endpoints
import data.httpapi.authz.whitelisted_endpoints

# Allow access to whitelisted endpoints
allow {
    some j
    regex.match(whitelisted_endpoints[j], input.requested_prefix)
}

allow {
    input.requested_prefix == "/"
}

# Allow users access to endpoints
allow {
    some i
    input.access_token.realm_access.roles[i] == "user"
    some j
    regex.match(allowed_user_endpoints[j], input.requested_prefix)
}

# Allow admin access to endpoints
allow {
    some i
    input.access_token.realm_access.roles[i] == "admin"
    some j
    regex.match(allowed_admin_endpoints[j], input.requested_prefix)
}