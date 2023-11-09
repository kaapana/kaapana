export function stringToColour(str) {
  if (str === "" || str === null) return "";
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  let colour = "#";
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xff;
    colour += ("00" + value.toString(16)).substr(-2);
  }
  return colour;
}

export function debounce(fn, delay) {
  let timeoutID = null;
  return function () {
    clearTimeout(timeoutID);
    const args = arguments;
    const that = this;
    timeoutID = setTimeout(function () {
      fn.apply(that, args);
    }, delay);
  };
}

export function checkRoleAuthR(policyData, endpoint, role, method = "GET" ) {
  "Check if role is authorized to access the requested endpoint with the requested method";
  let policyDataEndpoints = [];

  // Get a list of regular expressions for endpoints associated with the role
  policyDataEndpoints =
    policyData.endpoints_per_role && policyData.endpoints_per_role[role]
      ? policyData.endpoints_per_role[role]
      : [];

  /// Strip protocol and domain from the endpoint
  let strippedEndpoint;
  if (endpoint.includes("://")) {
    const endpointUrl = new URL(endpoint);
    strippedEndpoint = endpointUrl.pathname;
  } else {
    strippedEndpoint = endpoint;
  }

  // Test if the endpoint matches one of the regular expressions and if the method is allowed
  return policyDataEndpoints.some((restrictedEndpoint) =>
    new RegExp(restrictedEndpoint.path).test(strippedEndpoint) && restrictedEndpoint.methods.some((m) => m == method)
  );
}

export function checkAuthR(policyData, endpoint, user) {
  "Check if the user has a role that authorizes him to access the requested endpoint";
  return user.roles.some((role) => checkRoleAuthR(policyData, endpoint, role))
}