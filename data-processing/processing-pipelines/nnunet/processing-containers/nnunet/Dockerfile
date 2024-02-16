FROM local-only/base-nnunet:latest

LABEL IMAGE="nnunet-gpu"
LABEL VERSION="03-22"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/
WORKDIR /kaapana/app/

CMD ["bash","/kaapana/app/start_nnunet.sh"]