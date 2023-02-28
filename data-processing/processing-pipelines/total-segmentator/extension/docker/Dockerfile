FROM local-only/base-installer:latest

LABEL IMAGE="dag-total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_total_segmentator.py /kaapana/tmp/dags/
COPY files/totalsegmentator/TotalSegmentatorOperator.py /kaapana/tmp/dags/totalsegmentator/
COPY files/totalsegmentator/LocalGetTotalSegmentatorModelsOperator.py /kaapana/tmp/dags/totalsegmentator/
COPY files/pyradiomics/PyRadiomicsOperator.py /kaapana/tmp/dags/pyradiomics/
