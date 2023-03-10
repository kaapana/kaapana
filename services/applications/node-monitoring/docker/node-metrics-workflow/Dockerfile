FROM local-only/base-installer:latest

LABEL IMAGE="dag-node-metrics"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

COPY files/dag_metrics_collect_node.py /kaapana/tmp/dags/
COPY files/dag_metrics_collect_central.py /kaapana/tmp/dags/
COPY files/node_metrics /kaapana/tmp/dags/node_metrics