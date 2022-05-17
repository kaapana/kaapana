FROM local-only/dag-installer:0.1.0

LABEL IMAGE="dag-federated-setup-central-test"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_federated_setup_central_test.py /tmp/dags/
COPY files/federated_setup_central_test /tmp/dags/federated_setup_central_test

# COPY common/scripts/federated_setup_central_test /tmp/common/scripts/federated_setup_central_test