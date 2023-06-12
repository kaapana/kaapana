#!/bin/bash

HTTP_PROXY="http://www-int2.dkfz-heidelberg.de:80"
ADMIN_USER=`cat /stackrox_api_secret/username`
ADMIN_PASSWORD=`cat /stackrox_api_secret/password`
CLUSTER_NAME="stackrox-secured-cluster"

${HELM_PATH} -n stackrox install stackrox-central-services ./stackrox-central-services.tgz -o json --set central.adminPassword.value="${ADMIN_PASSWORD}"  --create-namespace --set central.persistence.persistentVolumeClaim.size=20 --set "env.proxyConfig=url: ${HTTP_PROXY}"

${KUBECTL_PATH} rollout status -n stackrox deployment central --timeout=120s
${KUBECTL_PATH} apply -f ./service.yaml 

${KUBECTL_PATH} -n stackrox exec deploy/central -- roxctl --insecure-skip-tls-verify --password "${ADMIN_PASSWORD}" central init-bundles generate stackrox-init-bundle --output - > ./stackrox-init-bundle.yaml

${HELM_PATH} install -n stackrox stackrox-secured-cluster-services ./stackrox-secured-cluster-services.tgz -f ./stackrox-init-bundle.yaml --set clusterName="$CLUSTER_NAME" --set "env.proxyConfig=url: ${HTTP_PROXY}"

# make the randomly generated api credentials available to security-pages
cp /stackrox_api_secret/username /api_credentials/stackrox_username
cp /stackrox_api_secret/password /api_credentials/stackrox_password