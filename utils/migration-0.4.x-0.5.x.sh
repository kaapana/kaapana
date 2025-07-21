#!/bin/bash
set -eu -o pipefail

if [ "$EUID" -ne 0 ]
then echo -e "Please run the script with root privileges!";
    exit 1
fi

# Check if FAST_DATA_DIR is provided
if [ $# -eq 0 ]; then
    echo "ERROR: No FAST_DATA_DIR provided."
    echo "Usage: $0 <FAST_DATA_DIR>"
    echo "Example: $0 /home/kaapana"
    exit 1
fi

FAST_DATA_DIR="$1"
echo "Using FAST_DATA_DIR: ${FAST_DATA_DIR}"

echo "Start migration -> Rename database folders in FAST_DATA_DIR"

mv "${FAST_DATA_DIR}/postgres-access-information-point" "${FAST_DATA_DIR}/access-information-interface-postgres-data"
mv "${FAST_DATA_DIR}/dicom-project-mapping-postgres" "${FAST_DATA_DIR}/dicom-web-filter-postgres-data"
mv "${FAST_DATA_DIR}/postgres-airflow" "${FAST_DATA_DIR}/airflow-postgres-data"
mv "${FAST_DATA_DIR}/postgres-backend" "${FAST_DATA_DIR}/kaapana-backend-postgres-data"

# Careful! Changed structure -> db-files subfolder removed
mv "${FAST_DATA_DIR}/keycloak/db-files" "${FAST_DATA_DIR}/keycloak-postgres-data"
rmdir "${FAST_DATA_DIR}/keycloak"

echo "Completed migration script successfully."
