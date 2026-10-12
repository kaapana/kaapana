FROM local-only/base-installer:latest

LABEL IMAGE="dag-auto-segmentation-pipeline"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_auto_segmentation_pipeline.py /kaapana/tmp/dags/
COPY files/dag_wsi_mapping.py /kaapana/tmp/dags/
COPY files/autosegmentationpipeline/ /kaapana/tmp/dags/autosegmentationpipeline/
