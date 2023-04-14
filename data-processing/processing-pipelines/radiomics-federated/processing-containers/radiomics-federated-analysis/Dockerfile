FROM local-only/base-installer:latest

LABEL IMAGE="radiomics-federated-analysis"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /files

CMD ["cp","-r","/files/.", "/target"]