FROM local-only/base-minio-mc:latest
LABEL IMAGE="nnunet-analysis-scripts"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

USER 0 
COPY files/ /files
CMD ["/bin/bash","/files/put_to_minio.sh"]
