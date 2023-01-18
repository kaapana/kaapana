FROM local-only/dag-installer:latest

LABEL IMAGE="avid"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY files/dag_avid_container_example.py /tmp/dags/
COPY files/dag_avid_python_example.py /tmp/dags/
COPY files/dag_example_form.py /tmp/dags
COPY files/avid /tmp/dags/avid_operator