FROM local-only/base-installer:latest

LABEL IMAGE="dag-classification-training-workflow"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_classification_training_workflow.py /kaapana/tmp/dags/
COPY files/dag_classification_inference_workflow.py /kaapana/tmp/dags/

COPY files/classification_training_workflow/TrainingOperator.py /kaapana/tmp/dags/classification_training_workflow/
COPY files/classification_training_workflow/PreprocessingOperator.py /kaapana/tmp/dags/classification_training_workflow/
COPY files/classification_inference_workflow/InferenceOperator.py /kaapana/tmp/dags/classification_inference_workflow/