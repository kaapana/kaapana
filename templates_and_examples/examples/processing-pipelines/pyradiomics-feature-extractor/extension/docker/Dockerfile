FROM local-only/base-installer:latest

LABEL IMAGE="dag-pyradiomics-extractor"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/dag_pyradiomics_extract_features.py /kaapana/tmp/dags/
COPY files/pyradiomics_extractor/PyradiomicsExtractorOperator.py /kaapana/tmp/dags/pyradiomics_extractor/
