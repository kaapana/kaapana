#!/bin/bash

# Define the path to the settings.xml file
SETTINGS_FILE="/tmp/settings.xml"

# Check if HTTP_PROXY is set and not equal to "false"
if [ -n "$HTTP_PROXY" ] && [ "$HTTP_PROXY" != "false" ]; then
  # Extract host and port from HTTP_PROXY
  PROXY_HOST=$(echo "${HTTP_PROXY#*//}" | cut -d ':' -f 1)
  PROXY_PORT=$(echo "${HTTP_PROXY##*:}")

  # Update the settings.xml file with the proxy configuration
  xmlstarlet ed --inplace \
    -u "/settings/proxies/proxy/host" -v "$PROXY_HOST" \
    -u "/settings/proxies/proxy/port" -v "$PROXY_PORT" \
    "$SETTINGS_FILE"

  echo "Proxy settings updated in $SETTINGS_FILE."
else
  # Remove the <proxies> field entirely from the settings.xml file
  xmlstarlet ed --inplace \
    -d "/settings/proxies" \
    "$SETTINGS_FILE"

  echo "No proxy settings. Removed <proxies> section from $SETTINGS_FILE."
fi
