FROM local-only/base-installer:latest

LABEL IMAGE="dag-service-ingestion"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_service_ingestion_trigger_rule.json /kaapana/tmp/dags/
COPY files/dag_service_ingestion.py /kaapana/tmp/dags/
COPY files/dag_ingest_data_upload.py /kaapana/tmp/dags/
COPY files/ingestion/LocalIngestionOperator.py /kaapana/tmp/dags/ingestion/
