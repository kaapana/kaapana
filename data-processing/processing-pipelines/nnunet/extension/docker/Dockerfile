FROM local-only/base-installer:latest

LABEL IMAGE="dag-nnunet"
LABEL VERSION="03-22"
LABEL CI_IGNORE="False"

COPY files/nnunet /kaapana/tmp/dags/nnunet
COPY files/dag_nnunet_model_install.py /kaapana/tmp/dags/
COPY files/dag_nnunet_model_uninstall.py /kaapana/tmp/dags/
COPY files/dag_nnunet_inference.py /kaapana/tmp/dags/
COPY files/dag_nnunet_training.py /kaapana/tmp/dags/
COPY files/dag_nnunet_ensemble.py /kaapana/tmp/dags/
