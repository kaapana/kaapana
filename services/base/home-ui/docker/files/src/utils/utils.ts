export function checkRoleAuthR(policyData: any, endpoint: string, role: string, method = 'GET') {
  'Check if role is authorized to access the requested endpoint with the requested method'
  let policyDataEndpoints = []

  policyDataEndpoints =
    policyData.endpoints_per_role && policyData.endpoints_per_role[role]
      ? policyData.endpoints_per_role[role]
      : []

  let strippedEndpoint
  if (endpoint.includes('://')) {
    const endpointUrl = new URL(endpoint)
    strippedEndpoint = endpointUrl.pathname
  } else {
    strippedEndpoint = endpoint
  }

  return policyDataEndpoints.some(
    (restrictedEndpoint: any) =>
      new RegExp(restrictedEndpoint.path).test(strippedEndpoint) &&
      restrictedEndpoint.methods.some((m: string) => m == method),
  )
}

export function checkAuthR(policyData: any, endpoint: string, user: any) {
  'Check if the user has a role that authorizes him to access the requested endpoint'
  return user.roles.some((role: string) => checkRoleAuthR(policyData, endpoint, role))
}
