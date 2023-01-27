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

mkdir ./config/wazuh_indexer_ssl_certs
mv /tmp-certificates/* ./config/wazuh_indexer_ssl_certs/

# without write permissions for other users the wazuh-indexer container fails to start
mkdir ./wazuh-indexer-data
chmod -R 777 ./wazuh-indexer-data

