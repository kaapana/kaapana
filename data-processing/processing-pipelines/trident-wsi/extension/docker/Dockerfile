FROM local-only/base-installer:latest

LABEL IMAGE="dag-trident-wsi"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_trident_tissue_segmentation.py /kaapana/tmp/dags/
COPY files/dag_trident_feature_extraction.py /kaapana/tmp/dags/
COPY files/trident_ops/ /kaapana/tmp/dags/trident_ops/
