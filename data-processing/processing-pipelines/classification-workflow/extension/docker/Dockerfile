FROM local-only/base-installer:latest

LABEL IMAGE="create-classification-dataset-workflow"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_create_classification_dataset.py /kaapana/tmp/dags/
COPY files/create-classification-dataset/CreateRawDatasetOperator.py /kaapana/tmp/dags/create_classification_dataset/