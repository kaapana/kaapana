echo "Waiting for OpenSearch service to be available..."
until curl --insecure -sS https://opensearch-service.${SERVICES_NAMESPACE}.svc:9200; do
echo "OpenSearch not available yet, retrying..."
sleep 5
done
echo "OpenSearch is now available!"
CONFIG_DIR="/usr/share/opensearch/config/"
SECURITY_CONFIG_DIR="${CONFIG_DIR}/opensearch-security"
MARKER_FILE="/usr/share/opensearch/logs/init-security-marker.txt"

if [ -f "${MARKER_FILE}" ]; then
  echo "OpenSearch security index already initialized, skipping security setup."
  exit 0
else
  echo "Init security extension from scratch."
  /usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh -icl -nhnv -cacert ${CONFIG_DIR}/root-ca.pem -cert ${CONFIG_DIR}/admin.pem -key ${CONFIG_DIR}/admin-key.pem -cd ${SECURITY_CONFIG_DIR} --hostname opensearch-service.${SERVICES_NAMESPACE}.svc
  echo "OpenSearch security index initialized successfully." > ${MARKER_FILE}
fi