FROM local-only/base-installer:latest

LABEL IMAGE="dag-tfda-execution-orchestrator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_tfda_execution_orchestrator.py /kaapana/tmp/dags/
COPY files/dag_isolated_container_execution.py /kaapana/tmp/dags/
COPY files/tfda_execution_orchestrator /kaapana/tmp/dags/tfda_execution_orchestrator