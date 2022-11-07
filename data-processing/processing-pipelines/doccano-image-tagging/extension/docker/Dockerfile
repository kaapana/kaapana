FROM local-only/dag-installer:latest

LABEL IMAGE="dag-doccano-image-tagging"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_service_parse_doccano_tokens.py /tmp/dags/
COPY files/dag_study_ids_to_doccano.py /tmp/dags/

COPY files/doccano /tmp/dags/doccano

