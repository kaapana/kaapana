package httpapi.authz

import future.keywords.every
import data.httpapi.authz.admin
import data.httpapi.authz.user
import data.httpapi.authz.whitelisted



# Allow admin access to endpoints
allow {
    some i
    input.access_token.realm_access.roles[i] == "admin"
    some j
    startswith(input.requested_prefix, admin[j])
}
# Allow users access to endpoints
allow {
    some i
    input.access_token.realm_access.roles[i] == "user"
    some j
    startswith(input.requested_prefix, user[j])
}
# Allow access to whitelisted endpoints
allow {
    some j
    startswith(input.requested_prefix, whitelisted[j])
}
allow {
    input.requested_prefix == "/"
}