FROM local-only/base-installer:latest

LABEL IMAGE="dag-persistence-layer-operators"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

COPY files/HelperPersistence.py /kaapana/tmp/dags/persistence/
COPY files/LocalGetUrnOperator.py /kaapana/tmp/dags/persistence/
COPY files/LocalPutCASOperator.py /kaapana/tmp/dags/persistence/
COPY files/dag_persistence_cas_upload.py /kaapana/tmp/dags/
COPY files/dag_persistence_urn_download.py /kaapana/tmp/dags/
