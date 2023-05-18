FROM local-only/base-installer:latest

LABEL IMAGE="dag-example"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_example_dcm2nrrd.py /kaapana/tmp/dags/
COPY files/dag_example_extract_multiple_study_ids.py /kaapana/tmp/dags/
COPY files/dag_example_extract_study_id.py /kaapana/tmp/dags/
COPY files/dag_example_pool_study_ids.py /kaapana/tmp/dags/
COPY files/example /kaapana/tmp/dags/example