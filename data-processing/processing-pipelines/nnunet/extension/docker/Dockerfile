FROM local-only/dag-installer:latest

LABEL IMAGE="dag-nnunet"
LABEL VERSION="03-22"
LABEL CI_IGNORE="False"

COPY files/nnunet /temp/dags/nnunet
COPY files/dag_nnunet_model_install.py /temp/dags/
COPY files/dag_nnunet_model_uninstall.py /temp/dags/
COPY files/dag_nnunet_inference.py /temp/dags/
COPY files/dag_nnunet_training.py /temp/dags/
COPY files/dag_nnunet_ensemble.py /temp/dags/
