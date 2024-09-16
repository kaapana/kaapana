echo "Waiting for OpenSearch service to be available..."
until curl --insecure -sS https://opensearch-service.${SERVICES_NAMESPACE}.svc:9200; do
echo "OpenSearch not available yet, retrying..."
sleep 5
done
echo "OpenSearch is now available!"
/usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh -icl -nhnv -cacert /usr/share/opensearch/config/root-ca.pem -cert /usr/share/opensearch/config/admin.pem -key /usr/share/opensearch/config/admin-key.pem -cd /usr/share/opensearch/config/opensearch-security --hostname opensearch-service.${SERVICES_NAMESPACE}.svc
