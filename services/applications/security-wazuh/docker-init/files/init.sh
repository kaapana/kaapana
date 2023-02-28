#!/bin/sh

# remove old config
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

# enable vulnerability detection
sed -i -z "s/<vulnerability-detector>\(\s*\)<enabled>no/<vulnerability-detector>\1<enabled>yes/g" ./config/wazuh_cluster/wazuh_manager.conf
#perl -i -pe 'BEGIN{undef $/;} s/<vulnerability-detector>\(.*\)<enabled>no/<vulnerability-detector>\1<enabled>yes/smg' ./config/wazuh_cluster/wazuh_manager.conf
sed -i -z "s/<provider name=\"canonical\">\(\s*\)<enabled>no/<provider name=\"canonical\">\1<enabled>yes/g" ./config/wazuh_cluster/wazuh_manager.conf
#perl -i -pe 'BEGIN{undef $/;} s/<provider name=\"canonical\">\(.*\)<enabled>no/<provider name=\"canonical\">\1<enabled>yes/smg' ./config/wazuh_cluster/wazuh_manager.conf
sed -i -z "s/<provider name=\"redhat\">\(\s*\)<enabled>no/<provider name=\"redhat\">\1<enabled>yes/g" ./config/wazuh_cluster/wazuh_manager.conf
#perl -i -pe 'BEGIN{undef $/;} s/<provider name=\"redhat\">\(.*\)<enabled>no/<provider name=\"redhat\">\1<enabled>yes/smg' ./config/wazuh_cluster/wazuh_manager.conf

# set sca interval to 30min
#perl -i -pe 'BEGIN{undef $/;} s/<sca>\(.*\)<interval>12h/<sca>\1<interval>30m/smg' ./config/wazuh_cluster/wazuh_manager.conf
sed -i -z "s/<sca>\(.*\)<interval>12h/<sca>\1<interval>30m/g" ./config/wazuh_cluster/wazuh_manager.conf

mkdir ./config/wazuh_indexer_ssl_certs
mv /tmp-certificates/* ./config/wazuh_indexer_ssl_certs/

# without write permissions for other users the wazuh-indexer container fails to start
mkdir ./wazuh-indexer-data >/dev/null 2>&1
chmod -R 777 ./wazuh-indexer-data

# make the randomly generated api credentials available to security-pages
cp /wazuh_api_secret/username /api_credentials/wazuh_username
cp /wazuh_api_secret/password /api_credentials/wazuh_password

# add shared agent config
mkdir -p /wazuh-agent-config/shared/default/
chmod -R 777 /wazuh-agent-config
cp /shared_agent_config.xml /wazuh-agent-config/shared/default/agent.conf