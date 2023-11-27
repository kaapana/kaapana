FROM local-only/base-installer:latest

LABEL IMAGE="dag-tfda-spe-orchestrator"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_tfda_spe_orchestrator.py /kaapana/tmp/dags/
COPY files/dag_isolated_container_execution.py /kaapana/tmp/dags/
COPY files/dag_spe_vm_orchestrator.py /kaapana/tmp/dags/
COPY files/dag_spe_pod_orchestrator.py /kaapana/tmp/dags/
COPY files/tfda_spe_orchestrator /kaapana/tmp/dags/tfda_spe_orchestrator