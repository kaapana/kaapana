export function stringToColour(str: string): string {
  if (str === '' || str === null) return ''
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  let colour = '#'
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xff
    colour += ('00' + value.toString(16)).substr(-2)
  }
  return colour
}

export function debounce(fn: (...args: any[]) => void, delay: number) {
  let timeoutID: ReturnType<typeof setTimeout> | null = null
  return function (this: any, ...args: any[]) {
    if (timeoutID) clearTimeout(timeoutID)
    const that = this
    timeoutID = setTimeout(function () {
      fn.apply(that, args)
    }, delay)
  }
}

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
