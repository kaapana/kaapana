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

cat >>./config/wazuh_dashboard/opensearch_dashboards.yml <<EOF

# Enable OpenID authentication
opensearch_security.auth.type: "openid"
# The IdP metadata endpoint
opensearch_security.openid.connect_url: "http://keycloak-external-service.admin.svc:80/auth/realms/kaapana/.well-known/openid-configuration"
# The ID of the OpenID Connect client in your IdP
opensearch_security.openid.client_id: "kaapana"
# The client secret of the OpenID Connect client
opensearch_security.openid.client_secret: "uQBJzc2YDzjRfj2OCT79JDShojeqAK2R"
# The base of the redirect URL that will be sent to your IdP. Optional. Only necessary when OpenSearch Dashboards is behind a reverse proxy, in which case it should be different than server.host and server.port in opensearch_dashboards.yml.
opensearch_security.openid.base_redirect_url: "https://vm-128-206.cloud.dkfz-heidelberg.de:443/security-wazuh"
EOF

API_USER=`cat /wazuh_api_secret/username`
API_PW=`cat /wazuh_api_secret/password`
sed -i "s/username: wazuh-wui/username: $API_USER/" ./config/wazuh_dashboard/wazuh.yml
sed -i "s/password: \"MyS3cr37P450r.*-\"/password: \"$API_PW\"/" ./config/wazuh_dashboard/wazuh.yml

# enable vulnerability detection
sed -i -z "s/<vulnerability-detector>\(\s*\)<enabled>no/<vulnerability-detector>\1<enabled>yes/g" ./config/wazuh_cluster/wazuh_manager.conf
sed -i -z "s/<provider name=\"canonical\">\(\s*\)<enabled>no/<provider name=\"canonical\">\1<enabled>yes/g" ./config/wazuh_cluster/wazuh_manager.conf
sed -i -z "s/<provider name=\"redhat\">\(\s*\)<enabled>no/<provider name=\"redhat\">\1<enabled>yes/g" ./config/wazuh_cluster/wazuh_manager.conf

# set sca interval to 30min
sed -i -z "s/<sca>\(.*\)<interval>12h/<sca>\1<interval>30m/g" ./config/wazuh_cluster/wazuh_manager.conf

mkdir ./config/wazuh_indexer_ssl_certs
mv /tmp-certificates/* ./config/wazuh_indexer_ssl_certs/

# without write permissions for other users the wazuh-indexer container fails to start
mkdir ./wazuh-indexer-data >/dev/null 2>&1
chmod -R 777 ./wazuh-indexer-data # TODO: set correct owner instead (find out which)

# make the randomly generated api credentials available to security-pages
cp /wazuh_api_secret/username /api_credentials/wazuh_username
cp /wazuh_api_secret/password /api_credentials/wazuh_password

# add shared agent config
mkdir -p /wazuh-agent-config/shared/default/
chmod -R 777 /wazuh-agent-config # TODO: set correct owner instead (find out which)
cp /shared_agent_config.xml /wazuh-agent-config/shared/default/agent.conf

cp /security_config.yml ./config/wazuh_indexer/security_config.yml
cp /roles_mapping.yml ./config/wazuh_indexer/roles_mapping.yml
