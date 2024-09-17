#!/bin/sh

echo "Checking registry connection to $REGISTRY_URL"
REGISTRY_URL=$1
REGISTRY_USERNAME=$2
REGISTRY_PASSWORD=$3
REGISTRY_AUTH=$(echo -n "$REGISTRY_USERNAME:$REGISTRY_PASSWORD" | base64)

result=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Basic $REGISTRY_AUTH" "https://${REGISTRY_URL}/v2/")
if [ $result -eq 200 ]; then
    echo "Connection successful!"
    exit 0
else
    echo "Failed to connect to the registry."
    exit 1
fi
