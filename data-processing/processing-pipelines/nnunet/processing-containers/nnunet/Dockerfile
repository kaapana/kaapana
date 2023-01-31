FROM local-only/base-nnunet:latest

LABEL IMAGE="nnunet-gpu"
LABEL VERSION="03-22"
LABEL CI_IGNORE="False"

COPY files/ /app/
WORKDIR /app/
CMD ["bash","/app/start_nnunet.sh"]