FROM local-only/base-installer:latest

LABEL IMAGE="dag-nnunet"
LABEL VERSION="03-22"
LABEL BUILD_IGNORE="False"

COPY files/nnunet /kaapana/tmp/dags/nnunet
COPY files/dag_nnunet_inference.py /kaapana/tmp/dags/
COPY files/dag_nnunet_training.py /kaapana/tmp/dags/
COPY files/dag_nnunet_ensemble.py /kaapana/tmp/dags/
COPY files/dag_nnunet_install_models.py /kaapana/tmp/dags/
COPY files/dag_nnunet_uninstall_models.py /kaapana/tmp/dags/
