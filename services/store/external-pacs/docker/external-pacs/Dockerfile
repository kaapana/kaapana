FROM local-only/base-installer:latest

LABEL IMAGE="dag-external-pacs"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_external_pacs_add.py /kaapana/tmp/dags/
COPY files/dag_external_pacs_remove.py /kaapana/tmp/dags/
COPY files/external_pacs /kaapana/tmp/dags/external_pacs