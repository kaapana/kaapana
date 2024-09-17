echo "Waiting for OpenSearch service to be available..."
until curl --insecure -sS https://opensearch-service.${SERVICES_NAMESPACE}.svc:9200; do
echo "OpenSearch not available yet, retrying..."
sleep 5
done
echo "OpenSearch is now available!"
CONFIG_DIR="/usr/share/opensearch/config/"
OPENSEARCH_BACK_UP_DIR="/kaapana/opensearch-security-backup"

if [ -d "${OPENSEARCH_BACK_UP_DIR}" ] && [ "$(ls -A ${OPENSEARCH_BACK_UP_DIR})" ]; then
  echo "Init security extension with back up files."
  SECURITY_CONFIG_DIR="${OPENSEARCH_BACK_UP_DIR}"
else
  echo "Init security extension from scratch."
  SECURITY_CONFIG_DIR="${CONFIG_DIR}/opensearch-security"
fi

/usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh -icl -nhnv -cacert ${CONFIG_DIR}/root-ca.pem -cert ${CONFIG_DIR}/admin.pem -key ${CONFIG_DIR}/admin-key.pem -cd ${SECURITY_CONFIG_DIR} --hostname opensearch-service.${SERVICES_NAMESPACE}.svc
