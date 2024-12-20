CONFIG_DIR="/usr/share/opensearch/config/"

/usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh -icl -nhnv -cacert ${CONFIG_DIR}/root-ca.pem -cert ${CONFIG_DIR}/admin.pem -key ${CONFIG_DIR}/admin-key.pem -backup /kaapana/opensearch-security-backup
