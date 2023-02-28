FROM local-only/base-installer:latest

LABEL IMAGE="dag-installer-template"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/templates /kaapana/tmp/dags/templates
COPY files/dag_template.py /kaapana/tmp/dags/