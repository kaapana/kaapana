FROM local-only/dag-installer:latest

LABEL IMAGE="dag-download-tcia-data"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dag_download_tcia_data.py /tmp/dags/
COPY files/tcia-download/TciaDownloadOperator.py /tmp/dags/tcia_download/