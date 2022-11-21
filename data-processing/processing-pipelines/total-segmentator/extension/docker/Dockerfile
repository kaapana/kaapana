FROM local-only/dag-installer:latest

LABEL IMAGE="dag-total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_total_segmentator.py /tmp/dags/
COPY files/totalsegmentator/TotalSegmentatorOperator.py /tmp/dags/totalsegmentator/
COPY files/totalsegmentator/LocalGetTotalSegmentatorModelsOperator.py /tmp/dags/totalsegmentator/
COPY files/pyradiomics/PyRadiomicsOperator.py /tmp/dags/pyradiomics/
