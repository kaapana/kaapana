FROM local-only/base-installer:latest

LABEL IMAGE="dag-liver-tumor-segmentation"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_liver_segmentation.py /kaapana/tmp/dags/
COPY files/liver-segmentation/LiverSegmentationOperator.py /kaapana/tmp/dags/liver_segmentation/
