FROM local-only/dag-installer:latest

LABEL IMAGE="dag-total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_total_segmentator.py /temp/dags/
COPY files/totalsegmentator/TotalSegmentatorOperator.py /temp/dags/totalsegmentator/
COPY files/totalsegmentator/LocalGetTotalSegmentatorModelsOperator.py /temp/dags/totalsegmentator/
COPY files/pyradiomics/PyRadiomicsOperator.py /temp/dags/pyradiomics/
