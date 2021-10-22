FROM local-only/dag-installer:0.1.0

# Build in kaapana/templates_and_examples/examples/workflows/airflow-components with:
# docker build -t registry.hzdr.de/kaapana/kaapana-devdag-treshhold-segmentation:0.1.0 -f ../dag-installer/treshhold-segmentation/Dockerfile.treshhold-segmentation .

LABEL IMAGE="dag-treshhold-segmentation"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY dags/dag_treshhold_segmentation.py /tmp/dags/
COPY dags/treshhold_segmentation /tmp/dags/treshhold_segmentation