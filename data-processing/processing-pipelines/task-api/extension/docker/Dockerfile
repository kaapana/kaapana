FROM local-only/base-installer:latest

LABEL IMAGE="dag-test-task-api"
LABEL VERSION="1.0.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_test_task_operator.py /kaapana/tmp/dags/
COPY files/dag_register_dicoms.py /kaapana/tmp/dags/
COPY files/task_api_operators/KaapanaTaskOperator.py /kaapana/tmp/dags/task_api_operators/
