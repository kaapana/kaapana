FROM local-only/dag-installer:latest

LABEL IMAGE="dag-tfda-execution-orchestrator"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

COPY files/dag_tfda_execution_orchestrator.py /tmp/dags/
COPY files/dag_tfda_testing_workflow.py /tmp/dags/
COPY files/tfda_execution_orchestrator /tmp/dags/tfda_execution_orchestrator