FROM local-only/base-minio-mc:latest
LABEL IMAGE="radiomics-federated-analysis"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

USER 0 
COPY files/ /files
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.1/build-scripts/constraints-0.2.1.txt --upgrade setuptools pip && pip3 install -r /files/requirements.txt

CMD ["/bin/bash","/files/put_to_minio.sh"]
