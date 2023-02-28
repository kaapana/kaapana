FROM local-only/base-installer:latest

LABEL IMAGE="dag-otsus-method"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_otsus_method.py /kaapana/tmp/dags/
COPY files/otsus-method/OtsusMethodOperator.py /kaapana/tmp/dags/otsus_method/
COPY files/otsus-method/OtsusNotebookOperator.py /kaapana/tmp/dags/otsus_method/