#!/bin/bash
set -eu -o pipefail

if [ "$EUID" -ne 0 ]; then
    echo -e "Please run the script with root privileges!"
    exit 1
fi

# Check if FAST_DATA_DIR and SLOW_DATA_DIR are provided
if [ $# -lt 2 ]; then
    echo "ERROR: Both FAST_DATA_DIR and SLOW_DATA_DIR must be provided."
    echo "Usage: $0 <FAST_DATA_DIR> <SLOW_DATA_DIR>"
    echo "Example: $0 /home/kaapana /mnt/slow_data"
    exit 1
fi

FAST_DATA_DIR="$1"
SLOW_DATA_DIR="$2"

echo "Using FAST_DATA_DIR: ${FAST_DATA_DIR}"
echo "Using SLOW_DATA_DIR: ${SLOW_DATA_DIR}"


echo "Start migration -> Rename database folders in FAST_DATA_DIR"

echo "Moving postgres-access-information-point → access-information-interface-postgres-data"
mv "${FAST_DATA_DIR}/postgres-access-information-point" "${FAST_DATA_DIR}/access-information-interface-postgres-data"

echo "Moving dicom-project-mapping-postgres → dicom-web-filter-postgres-data"
mv "${FAST_DATA_DIR}/dicom-project-mapping-postgres" "${FAST_DATA_DIR}/dicom-web-filter-postgres-data"

echo "Moving postgres-airflow → airflow-postgres-data"
mv "${FAST_DATA_DIR}/postgres-airflow" "${FAST_DATA_DIR}/airflow-postgres-data"

echo "Moving postgres-backend → kaapana-backend-postgres-data"
mv "${FAST_DATA_DIR}/postgres-backend" "${FAST_DATA_DIR}/kaapana-backend-postgres-data"

# Careful! Changed structure -> db-files subfolder removed
echo "Moving keycloak/db-files → keycloak-postgres-data"
mv "${FAST_DATA_DIR}/keycloak/db-files" "${FAST_DATA_DIR}/keycloak-postgres-data"

echo "Removing empty keycloak directory"
rmdir "${FAST_DATA_DIR}/keycloak"

echo "Completed migration script successfully."
