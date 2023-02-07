FROM local-only/dag-installer:latest

LABEL IMAGE="dag-otsus-method"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_otsus_method.py /temp/dags/
COPY files/otsus-method/OtsusMethodOperator.py /temp/dags/otsus_method/
COPY files/otsus-method/OtsusNotebookOperator.py /temp/dags/otsus_method/
