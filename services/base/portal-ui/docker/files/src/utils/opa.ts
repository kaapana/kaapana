// policyData comes from GET /kaapana-backend/open-policy-data.

export interface PolicyEndpoint {
  path: string
  methods: string[]
}

export interface PolicyData {
  endpoints_per_role?: Record<string, PolicyEndpoint[]>
}

export interface OpaUser {
  roles: string[]
}

/** Check if a role is authorized to access the endpoint with the given method. */
export function checkRoleAuthR(
  policyData: PolicyData,
  endpoint: string,
  role: string,
  method = 'GET',
): boolean {
  const policyDataEndpoints =
    (policyData.endpoints_per_role && policyData.endpoints_per_role[role]) || []

  let strippedEndpoint: string
  if (endpoint.includes('://')) {
    strippedEndpoint = new URL(endpoint).pathname
  } else {
    strippedEndpoint = endpoint
  }

  return policyDataEndpoints.some(
    (restrictedEndpoint) =>
      new RegExp(restrictedEndpoint.path).test(strippedEndpoint) &&
      restrictedEndpoint.methods.some((m) => m == method),
  )
}

/** Check if the user has any role that authorizes access to the endpoint. */
export function checkAuthR(policyData: PolicyData, endpoint: string, user: OpaUser): boolean {
  return user.roles.some((role) => checkRoleAuthR(policyData, endpoint, role))
}
