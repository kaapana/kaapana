FROM local-only/dag-installer:latest

LABEL IMAGE="dag-nnunet"
LABEL VERSION="03-22"
LABEL CI_IGNORE="False"

COPY files/nnunet /tmp/dags/nnunet
COPY files/dag_nnunet_model_install.py /tmp/dags/
COPY files/dag_nnunet_model_uninstall.py /tmp/dags/
COPY files/dag_nnunet_inference.py /tmp/dags/
COPY files/dag_nnunet_training.py /tmp/dags/
COPY files/dag_nnunet_ensemble.py /tmp/dags/
