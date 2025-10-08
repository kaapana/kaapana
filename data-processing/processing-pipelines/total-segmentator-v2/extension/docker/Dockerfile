FROM local-only/base-installer:latest

LABEL IMAGE="dag-total-segmentator-v2"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_total_segmentator_v2.py /kaapana/tmp/dags/
COPY files/totalsegmentator/TotalSegmentatorV2Operator.py /kaapana/tmp/dags/totalsegmentator/
COPY files/pyradiomics/PyRadiomicsOperator.py /kaapana/tmp/dags/pyradiomics/
