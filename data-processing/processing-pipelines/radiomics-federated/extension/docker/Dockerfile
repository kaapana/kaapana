FROM local-only/base-installer:latest

LABEL IMAGE="dag-radiomics-federated"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_radiomics_federated_central.py /kaapana/tmp/dags/
COPY files/dag_radiomics_federated_node.py /kaapana/tmp/dags/
COPY files/radiomics_federated /kaapana/tmp/dags/radiomics_federated