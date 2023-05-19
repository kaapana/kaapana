FROM local-only/base-installer:latest

LABEL IMAGE="dag-m2olie"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

COPY files/dag_image_registration.py /kaapana/tmp/dags/
COPY files/dag_image_segmentation.py /kaapana/tmp/dags/
COPY files/m2olie /kaapana/tmp/dags/m2olie