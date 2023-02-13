#!/bin/sh

# remove 

if [ -d "./config" ]; then
    rm -rf ./config
fi
mkdir ./config
mv /tmp-config/* ./config 

sed -i '1i server.basePath: "/security-wazuh"' ./config/wazuh_dashboard/opensearch_dashboards.yml
sed -i '1a server.rewriteBasePath: true' ./config/wazuh_dashboard/opensearch_dashboards.yml
sed -i 's/opensearch.ssl.verificationMode: certificate/opensearch.ssl.verificationMode: none/' ./config/wazuh_dashboard/opensearch_dashboards.yml
sed -i 's/server.ssl.enabled: true/server.ssl.enabled: false/' ./config/wazuh_dashboard/opensearch_dashboards.yml

API_USER=`cat /wazuh_api_secret/username`
API_PW=`cat /wazuh_api_secret/password`
sed -i "s/username: wazuh-wui/username: $API_USER/" ./config/wazuh_dashboard/wazuh.yml
sed -i "s/password: \"MyS3cr37P450r.*-\"/password: \"$API_PW\"/" ./config/wazuh_dashboard/wazuh.yml

mkdir ./config/wazuh_indexer_ssl_certs
mv /tmp-certificates/* ./config/wazuh_indexer_ssl_certs/

# without write permissions for other users the wazuh-indexer container fails to start
mkdir ./wazuh-indexer-data
chmod -R 777 ./wazuh-indexer-data

# make the randomly generated api credentials available to security-pages
cp /wazuh_api_secret/username /api_credentials/wazuh_username
cp /wazuh_api_secret/password /api_credentials/wazuh_password
